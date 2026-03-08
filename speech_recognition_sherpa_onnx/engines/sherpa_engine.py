import os
import sys
import numpy as np
import sherpa_onnx
import onnxruntime as ort
import soundfile as sf
import traceback

from .base_engine import BaseEngine
from . import sherpa_utils

class SherpaEngine(BaseEngine):
    @staticmethod
    def determine_device(device_param, logger=None):
        if device_param != "auto" and device_param != "":
            return device_param
        available_providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in available_providers:
            return "cuda"
        elif 'CoreMLExecutionProvider' in available_providers:
            return "coreml"
        else:
            return "cpu"

    def __init__(self, node):
        super().__init__(node)
        self.node.declare_parameter('model_name', 'sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06')
        self.node.declare_parameter('device', 'auto')
        
        model_name_param = self.node.get_parameter('model_name').value
        if model_name_param.startswith(('/', '~')):
            self.model_dir = os.path.expanduser(model_name_param).rstrip("/\\")
        else:
            self.model_dir = os.path.expanduser(os.path.join("~/.sherpa_onnx_asr_models/", model_name_param)).rstrip("/\\")
        self.node.get_logger().info(f"[*] Model Configuration:")
        self.node.get_logger().info(f"    - Name: '{model_name_param}'")
        self.node.get_logger().info(f"    - Path: {self.model_dir}")

        self.is_streamable = False 
        self.use_external_vad = True
        self.config = self._build_config_from_node()
        self.global_settings = self.config.get('global_settings', {})
        self.online_config = self.config.get('streaming_models', {})
        self.offline_config = self.config.get('batch_models', {})
        self.decoding_method = self.global_settings.get('decoding_method', 'greedy_search')
        self.default_num_threads = 2
        
        device_param = self.node.get_parameter('device').value
        self.device = self.determine_device(device_param, self.node.get_logger())
        self.recognizer = None

        self._load_model()

    def _load_model(self):
        try:
            if not os.path.exists(self.model_dir):
                raise FileNotFoundError(f"Model directory not found: {self.model_dir}")
            
            onnx_files = [f for f in os.listdir(self.model_dir) if f.endswith(".onnx")]
            if not onnx_files:
                npu_formats = [os.path.splitext(f)[1] for f in os.listdir(self.model_dir) if f.endswith((".om", ".rknn"))]
                if npu_formats:
                    raise TypeError(
                        f"[Unsupported Format] The model in '{os.path.basename(self.model_dir)}' uses {npu_formats[0]} format (NPU specific). "
                        "This engine only supports .onnx models. Please download the ONNX version."
                    )
                else:
                    pass 

            files_in_dir = os.listdir(self.model_dir)
            is_funasr_nano = any("llm" in f.lower() for f in files_in_dir)
            if not is_funasr_nano:
                is_mine, reason = sherpa_utils.is_landmine_model(self.model_dir)
                if is_mine:
                    raise TypeError(f"[Landmine Detected] {reason}")
            
            dir_name = os.path.basename(self.model_dir).lower()
            if ("streaming" in dir_name) or ("online" in dir_name):
                self.is_streaming = True
                self.use_external_vad = False
            else:
                self.is_streaming = False
                self.use_external_vad = True

            if self.is_streaming:
                self.node.get_logger().info(f"[*] Detection Mode: Online (Streaming)")
                self._init_online()
            else:
                self.node.get_logger().info(f"[*] Detection Mode: Offline (Batch)")
                self._init_offline()

            if self.recognizer:
                self._run_dummy_check()
                
        except Exception as e:
            self.node.get_logger().error(f"!!! CRITICAL ERROR DURING MODEL LOAD: {e}")
            self.node.get_logger().error(traceback.format_exc())
            raise e

    def _build_config_from_node(self):
        import yaml
        path = self.node.get_parameter_or('config_path', type('',(),{'value':''})).value
        if not path:
            from ament_index_python.packages import get_package_share_directory
            path = os.path.join(get_package_share_directory('speech_recognition_sherpa_onnx'), 'config', 'params.yaml')

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                cfg = data.get('/**', {}).get('ros__parameters', data.get('sherpa_onnx_server', {}).get('ros__parameters', data))
                
                self.node.get_logger().info(f"[*] Config loaded: {path}")
                return {k: cfg.get(k, {}) for k in ['global_settings', 'streaming_models', 'batch_models']}
        except Exception as e:
            self.node.get_logger().error(f"Load failed: {e}")
            return {k: {} for k in ['global_settings', 'streaming_models', 'batch_models']}

    def _get_model_conf(self, model_key):
        parent = self.online_config if self.is_streaming else self.offline_config
        source = "streaming_models" if self.is_streaming else "batch_models"
        conf = parent.get(model_key, {}).copy()
        if 'num_threads' not in conf:
            conf['num_threads'] = self.default_num_threads
        self.node.get_logger().info(f"    - [Config] {model_key} (from {source}): threads={conf['num_threads']}")
        return conf

    def _find(self, *keywords): 
        return sherpa_utils.find_file(self.model_dir, *keywords)
    
    def _find_recursive(self, filename):
        return sherpa_utils.find_recursive(self.model_dir, filename)

    def _find_tokens(self): 
        return sherpa_utils.find_tokens(self.model_dir)

    def _init_online(self):
        self.is_streamable = True
        tokens = self._find_tokens()
        encoder = self._find("encoder")
        decoder = self._find("decoder")
        joiner = self._find("joiner")    
        model_type = sherpa_utils.inspect_online_model_type(self.model_dir)
        self.node.get_logger().info(f" -> [Auto-Detect] Identified Online Type: [{model_type.upper()}]")
        
        conf = self._get_model_conf(model_type)
        num_threads = conf.get('num_threads', 2)

        enable_ep = self.online_config.get('enable_endpoint_detection', False)
        r1 = self.online_config.get('rule1_min_trailing_silence', 2.4)
        r2 = self.online_config.get('rule2_min_trailing_silence', 1.2)
        r3 = self.online_config.get('rule3_min_utterance_length', 20.0)

        print(f"    - Endpoint Detection: {enable_ep} (R1={r1}s, R2={r2}s, R3={r3}s)")

        common_args = {
            "tokens": tokens, "num_threads": num_threads, "sample_rate": 16000, "feature_dim": 80,
            "decoding_method": self.decoding_method, "provider": self.device,
            "enable_endpoint_detection": enable_ep, "rule1_min_trailing_silence": r1,
            "rule2_min_trailing_silence": r2, "rule3_min_utterance_length": r3
        }

        if model_type == "transducer":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=self._find("encoder"), decoder=self._find("decoder"), joiner=self._find("joiner"),
                max_active_paths=conf.get("max_active_paths", 4),
                blank_penalty=conf.get("blank_penalty", 0.0),
                temperature_scale=conf.get("temperature_scale", 2.0), **common_args
            )
        elif model_type == "paraformer":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
                encoder=self._find("encoder"), decoder=self._find("decoder"), **common_args
            )
        elif model_type == "wenet_ctc":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_wenet_ctc(
                model=self._find("model"), chunk_size=conf.get('chunk_size', 16),
                num_left_chunks=conf.get('num_left_chunks', 4), **common_args
            )
        elif model_type == "zipformer2_ctc":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(model=self._find("model"), **common_args)
        elif model_type == "nemo_ctc":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_nemo_ctc(model=self._find("model"), **common_args)
        elif model_type == "t_one_ctc":
            common_args["sample_rate"] = 8000
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_t_one_ctc(model=self._find("model"), **common_args)
        else:
            raise ValueError(f"Unknown online model type: {model_type}")

    def _init_offline(self):
        model_file = self._find("model") or self._find("encoder") or self._find("encode") or self._find("llm")
        tokens = self._find_tokens()
        model_type = sherpa_utils.inspect_offline_model_type(self.model_dir)
        self.node.get_logger().info(f" -> [Auto-Detect] Identified Offline Type: [{model_type.upper()}]")        
        conf = self._get_model_conf(model_type)
        num_threads = conf.get('num_threads', 2)

        if model_type == "fun_asr_nano":
            encoder_adaptor = self._find("encoder_adaptor")
            llm = self._find("llm")
            embedding = self._find("embedding")
            
            tokenizer_dir = self.model_dir 
            try:
                for entry in os.listdir(self.model_dir):
                    if os.path.isdir(os.path.join(self.model_dir, entry)) and "Qwen" in entry:
                        tokenizer_dir = os.path.join(self.model_dir, entry)
                        break
            except Exception as e:
                self.node.get_logger().warning(f"Could not find tokenizer directory for FunASR Nano: {e}")

            self.recognizer = sherpa_onnx.OfflineRecognizer.from_funasr_nano(
                encoder_adaptor=self._find("encoder_adaptor"), llm=self._find("llm"),
                embedding=self._find("embedding"), tokenizer=tokenizer_dir, num_threads=num_threads,
                provider=self.device, system_prompt=conf.get("system_prompt", "You are a helpful assistant."),
                user_prompt=conf.get("user_prompt", "语音转写:"), max_new_tokens=conf.get("max_new_tokens", 512),
                temperature=conf.get("temperature", 1e-6), top_p=conf.get("top_p", 0.8), 
                seed=conf.get("seed", 42), language=conf.get("language", "")
            )
        elif model_type == "nemo_canary":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_canary(
                encoder=self._find("encoder"), decoder=self._find("decoder"), tokens=tokens,
                src_lang=conf.get('src_lang', 'en'), tgt_lang=conf.get('tgt_lang', 'en'),
                num_threads=num_threads, feature_dim=128, provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "sense_voice":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_file, tokens=tokens, num_threads=num_threads, use_itn=conf.get('use_itn', True),
                language=conf.get('language', ''), provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "whisper":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=self._find("encoder"), decoder=self._find("decoder"), tokens=tokens, 
                language=conf.get('language', 'en'), task=conf.get('task', 'transcribe'),
                tail_paddings=conf.get('tail_paddings', -1),
                num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "moonshine":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
                preprocessor=self._find("preprocess"), encoder=model_file,
                uncached_decoder=self._find("uncached"), cached_decoder=self._find("cached"),
                tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method 
            )
        elif model_type == "fire_red_asr":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_fire_red_asr(
                encoder=self._find("encoder"), decoder=self._find("decoder"),
                tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method 
            )
        elif model_type == "transducer":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=self._find("encoder"), decoder=self._find("decoder"), joiner=self._find("joiner"),
                tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method,
                max_active_paths=conf.get("max_active_paths", 4), blank_penalty=conf.get("blank_penalty", 0.0)
            )
        elif model_type == "dolphin":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_dolphin_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "medasr":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_medasr_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "zipformer":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_zipformer_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "telespeech":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_telespeech_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, feature_dim=40, provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "omnilingual":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "tdnn":
            sr = 8000 if "yesno" in self.model_dir.lower() else 16000
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_tdnn_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, sample_rate=sr, feature_dim=23, 
                provider=self.device, decoding_method=self.decoding_method
            )
        elif model_type == "wenet":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_wenet_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, provider=self.device
            )
        elif model_type == "paraformer":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=model_file, tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method
            )
        else:
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads, provider=self.device, decoding_method=self.decoding_method
            )

    def _run_dummy_check(self):
        self.node.get_logger().info(">>> [Self-Check] Running sanity check...")
        try:
            dummy_audio = np.zeros(16000 * 2, dtype=np.float32) 
            s = self.recognizer.create_stream()
            s.accept_waveform(16000, dummy_audio)
            
            if self.is_streaming:
                while self.recognizer.is_ready(s):
                    self.recognizer.decode_stream(s)
            else:
                self.recognizer.decode_stream(s)
            self.node.get_logger().info(">>> [Self-Check] Successful")
        except Exception as e:
            self.node.get_logger().error(f">>> [Self-Check] Failed: {e}")
            raise e

    def create_stream(self):
        return self.recognizer.create_stream()

    def process_stream(self, stream):
        if self.is_streaming:
            while self.recognizer.is_ready(stream):
                self.recognizer.decode_stream(stream)
            result = self.recognizer.get_result(stream)
            return result.text.strip() if hasattr(result, "text") else str(result)
        else:
            self.recognizer.decode_stream(stream)
            if hasattr(stream, "result"):
                return stream.result.text.strip()
            return ""
    
    def transcribe(self, audio_path):
        if not os.path.exists(audio_path): return ""
        try:
            audio, sr = sf.read(audio_path, dtype='float32')
            if len(audio.shape) > 1: audio = audio[:, 0]
            stream = self.create_stream()
            stream.accept_waveform(sr, audio)
            if self.is_streaming:
                stream.input_finished()
                while self.recognizer.is_ready(stream):
                    self.recognizer.decode_stream(stream)
                
                result = self.recognizer.get_result(stream)
                return result.text.strip() if hasattr(result, "text") else str(result).strip()
            else:
                self.recognizer.decode_stream(stream)
                if hasattr(stream, "result"):
                    return stream.result.text.strip()
                return ""
            
        except Exception as e:
            self.node.get_logger().error(f"[Sherpa] Transcription error: {e}")
            self.node.get_logger().error(traceback.format_exc())
            return ""

    def put_chunk(self, chunk_np):
        if not self.is_streaming or self.recognizer is None:
            return None
            
        if not hasattr(self, 'current_stream') or self.current_stream is None:
            self.current_stream = self.create_stream()
            self.last_text = ""

        samples = chunk_np.astype(np.float32) / 32768.0
        self.current_stream.accept_waveform(16000, samples)
        
        while self.recognizer.is_ready(self.current_stream):
            self.recognizer.decode_stream(self.current_stream)
        
        result = self.recognizer.get_result(self.current_stream)
        full_text = result.text.strip() if hasattr(result, 'text') else str(result).strip()

        if self.recognizer.is_endpoint(self.current_stream):
            diff_text = full_text[len(self.last_text):].strip()
            self.recognizer.reset(self.current_stream)
            self.last_text = ""
            return diff_text if diff_text else None

        if full_text and len(full_text) > len(self.last_text):
            diff_text = full_text[len(self.last_text):].strip()
            if diff_text:
                self.last_text = full_text
                return diff_text
        return None