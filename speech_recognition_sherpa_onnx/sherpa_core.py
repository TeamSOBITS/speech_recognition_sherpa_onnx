import os
import sys
import numpy as np
import sherpa_onnx
import onnxruntime as ort

from . import sherpa_utils

try:
    import sherpa_onnx.online_recognizer
except ImportError:
    pass

class SherpaEngine:
    @staticmethod
    def determine_device(device_param, logger=None):
        if device_param != "auto":
            return device_param
        available_providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in available_providers:
            return "cuda"
        elif 'CoreMLExecutionProvider' in available_providers:
            return "coreml"
        else:
            return "cpu"

    def __init__(self, model_dir, device="cpu", config=None):
        self.model_dir = os.path.expanduser(model_dir).rstrip("/\\")

        YELLOW = '\033[93m'
        ENDC = '\033[0m'
        is_mine, reason = sherpa_utils.is_landmine_model(self.model_dir)
        if is_mine:
            raise TypeError(
                f"[Landmine Detected] The model in '{os.path.basename(self.model_dir)}' "
                f"{YELLOW}cannot be used with this engine. Reason: {reason}{ENDC}"
            )
        self.device = device
        self.recognizer = None
        self.is_streaming = False 

        self.config = config if config is not None else {}
        self.global_settings = self.config.get('global_settings', {})
        self.online_config = self.config.get('streaming_models', {})
        self.offline_config = self.config.get('batch_models', {})
        self.decoding_method = self.global_settings.get('decoding_method', 'greedy_search')
        self.default_num_threads = 2

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

        dir_name = os.path.basename(self.model_dir).lower()
        has_encoder = self._find("encoder") is not None
        has_decoder = self._find("decoder") is not None
        has_joiner = self._find("joiner") is not None
        
        if ("streaming" in dir_name) or ("online" in dir_name):
            self.is_streaming = True
        else:
            self.is_streaming = False

        if self.is_streaming:
            print(f"[*] Detection Mode: Online (Streaming)")
            self._init_online()
        else:
            print(f"[*] Detection Mode: Offline (Batch)")
            self._init_offline()

        if self.recognizer:
            self._run_dummy_check()

    def _get_model_conf(self, model_key):
        if self.is_streaming:
            parent_config = self.online_config
            source_name = "streaming_models"
        else:
            parent_config = self.offline_config
            source_name = "batch_models"

        m_conf = parent_config.get(model_key, {}).copy()
        
        if 'num_threads' not in m_conf:
            m_conf['num_threads'] = self.default_num_threads
            print(f"    - [Config] {model_key} (from {source_name}): using global num_threads ({self.default_num_threads})")
        else:
            print(f"    - [Config] {model_key} (from {source_name}): using specific num_threads ({m_conf['num_threads']})")
            
        return m_conf

    def _find(self, *keywords):
        return sherpa_utils.find_file(self.model_dir, *keywords)

    def _find_recursive(self, filename):
        return sherpa_utils.find_recursive(self.model_dir, filename)

    def _find_tokens(self):
        return sherpa_utils.find_tokens(self.model_dir)

    def _init_online(self):
        tokens = self._find_tokens()
        encoder = self._find("encoder")
        decoder = self._find("decoder")
        joiner = self._find("joiner")
        model_type = sherpa_utils.inspect_online_model_type(self.model_dir)
        
        print(f" -> [Auto-Detect] Identified Online Model Type: [{model_type.upper()}]")
        
        conf = self._get_model_conf(model_type)
        num_threads = conf.get('num_threads', 2)

        enable_endpoint = self.online_config.get('enable_endpoint_detection', False)
        rule1 = self.online_config.get('rule1_min_trailing_silence', 2.4)
        rule2 = self.online_config.get('rule2_min_trailing_silence', 1.2)
        rule3 = self.online_config.get('rule3_min_utterance_length', 20.0)
        
        print(f"    - Endpoint Detection: {enable_endpoint} (R1={rule1}s, R2={rule2}s, R3={rule3}s)")

        if model_type == "transducer":
            max_active_paths = conf.get("max_active_paths", 4)
            blank_penalty = conf.get("blank_penalty", 0.0)
            temperature_scale = conf.get("temperature_scale", 2.0)
            
            print(f"    - Transducer Config: MaxPaths={max_active_paths}, "
                  f"BlankPenalty={blank_penalty}, TempScale={temperature_scale}")

            self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                tokens=tokens,
                num_threads=num_threads,
                sample_rate=16000,
                feature_dim=80,
                decoding_method=self.decoding_method,
                max_active_paths=max_active_paths,
                blank_penalty=blank_penalty,
                temperature_scale=temperature_scale,
                provider=self.device,
                enable_endpoint_detection=enable_endpoint,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3
            )

        elif model_type == "paraformer":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
                tokens=tokens,
                encoder=self._find("encoder"),
                decoder=self._find("decoder"),
                num_threads=num_threads,
                sample_rate=16000,
                feature_dim=80,
                provider=self.device,
                decoding_method=self.decoding_method,
                enable_endpoint_detection=enable_endpoint,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3
            )

        elif model_type == "wenet_ctc":
            chunk_size = conf.get('chunk_size', 16)
            num_left_chunks = conf.get('num_left_chunks', 4)
            print(f"    - WeNet Config: chunk_size={chunk_size}, num_left_chunks={num_left_chunks}")
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_wenet_ctc(
                tokens=tokens,
                model=self._find("model"),
                chunk_size=chunk_size,
                num_left_chunks=num_left_chunks,
                num_threads=num_threads,
                sample_rate=16000,
                feature_dim=80,
                provider=self.device,
                decoding_method=self.decoding_method,
                enable_endpoint_detection=enable_endpoint,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3
            )

        elif model_type == "zipformer2_ctc":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
                tokens=tokens,
                model=self._find("model"),
                num_threads=num_threads,
                sample_rate=16000,
                feature_dim=80,
                provider=self.device,
                decoding_method=self.decoding_method,
                enable_endpoint_detection=enable_endpoint,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3
            )

        elif model_type == "nemo_ctc":
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_nemo_ctc(
                tokens=tokens,
                model=self._find("model"),
                num_threads=num_threads,
                sample_rate=16000,
                feature_dim=80,
                provider=self.device,
                decoding_method=self.decoding_method,
                enable_endpoint_detection=enable_endpoint,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3
            )

        elif model_type == "t_one_ctc":
            sr = 8000
            print(f"    - Sample Rate: {sr} (T-One Specific)")
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_t_one_ctc(
                tokens=tokens,
                model=self._find("model"),
                num_threads=num_threads,
                sample_rate=sr,
                feature_dim=80,
                provider=self.device,
                decoding_method=self.decoding_method,
                enable_endpoint_detection=enable_endpoint,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3
            )
        
        else:
            raise ValueError(f"Unknown online model type: {model_type}")
        print(" --------------------------------------------------")

    def _init_offline(self):
        model_file = self._find("model") or self._find("encoder") or self._find("encode") or self._find("llm")
        tokens = self._find_tokens()
        model_type = sherpa_utils.inspect_offline_model_type(self.model_dir)
        print(f" -> [Auto-Detect] Identified Model Type: [{model_type.upper()}]")        
        conf = self._get_model_conf(model_type)
        num_threads = conf.get('num_threads', 2)
        
        if model_type == "fun_asr_nano":
            encoder_adaptor = self._find(self.model_dir, "encoder_adaptor")
            llm = self._find(self.model_dir, "llm")
            embedding = self._find(self.model_dir, "embedding")
            
            tokenizer_dir = self.model_dir 
            try:
                for entry in os.listdir(self.model_dir):
                    full_path = os.path.join(self.model_dir, entry)
                    if os.path.isdir(full_path) and "Qwen" in entry:
                        tokenizer_dir = full_path
                        print(f"    - [Config] Found tokenizer directory: {entry}")
                        break
            except Exception:
                pass

            if not (encoder_adaptor and llm and embedding):
                raise ValueError("FunASR-Nano requires 'encoder_adaptor.onnx', 'llm.onnx', and 'embedding.onnx'.")
            
            system_prompt = conf.get("system_prompt", "You are a helpful assistant.")
            user_prompt = conf.get("user_prompt", "语音转写:")
            max_new_tokens = conf.get("max_new_tokens", 512)
            temperature = conf.get("temperature", 1e-6)
            top_p = conf.get("top_p", 0.8)
            seed = conf.get("seed", 42)

            self.recognizer = sherpa_onnx.OfflineRecognizer.from_funasr_nano(
                encoder_adaptor=encoder_adaptor,
                llm=llm,
                embedding=embedding,
                tokenizer=tokenizer_dir,
                num_threads=num_threads,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                debug=False,
                provider=self.device,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                seed=seed
            )

        elif model_type == "nemo_canary":
            src_lang = conf.get('src_lang', 'en')
            tgt_lang = conf.get('tgt_lang', 'en')
            print(f"    - Canary Config: Src={src_lang} -> Tgt={tgt_lang}")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_canary(
                encoder=self._find("encoder"),
                decoder=self._find("decoder"),
                tokens=tokens,
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                num_threads=num_threads,
                sample_rate=16000,
                feature_dim=128,
                decoding_method=self.decoding_method,
                provider=self.device
            )

        elif model_type == "sense_voice":
            language = conf.get('language', '')      
            use_itn = conf.get('use_itn', True)
            print(f"    - Language: '{language}', Use ITN: {use_itn}")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_file, 
                tokens=tokens, 
                num_threads=num_threads, 
                use_itn=use_itn, 
                language=language, 
                provider=self.device,
                sample_rate=16000,
                feature_dim=80,
                decoding_method=self.decoding_method
            )

        elif model_type == "whisper":
            language = conf.get('language', 'en')
            task = conf.get('task', 'transcribe')
            tail_paddings = conf.get('tail_paddings', -1)
            print(f"    - Language: {language}, Task: {task}")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=self._find("encoder"), 
                decoder=self._find("decoder"),
                tokens=tokens, 
                language=language, 
                task=task,
                tail_paddings=tail_paddings,
                num_threads=num_threads, 
                provider=self.device,
                decoding_method=self.decoding_method
            )

        elif model_type == "moonshine":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
                preprocessor=self._find("preprocess"), 
                encoder=self._find("encoder") or self._find("encode"),
                uncached_decoder=self._find("uncached"), 
                cached_decoder=self._find("cached"),
                tokens=tokens, 
                num_threads=num_threads, 
                provider=self.device,
                decoding_method=self.decoding_method 
            )

        elif model_type == "fire_red_asr":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_fire_red_asr(
                encoder=self._find("encoder"), 
                decoder=self._find("decoder"),
                tokens=tokens, 
                num_threads=num_threads, 
                provider=self.device,
                decoding_method=self.decoding_method 
            )

        elif model_type == "transducer":
            max_active_paths = conf.get("max_active_paths", 4)
            blank_penalty = conf.get("blank_penalty", 0.0)
            print(f"    - Max Active Paths: {max_active_paths}")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=self._find("encoder"), 
                decoder=self._find("decoder"), 
                joiner=self._find("joiner"),
                tokens=tokens, 
                num_threads=num_threads, 
                sample_rate=16000, 
                feature_dim=80, 
                provider=self.device,
                decoding_method=self.decoding_method, 
                max_active_paths=max_active_paths,
                blank_penalty = blank_penalty
            )

        elif model_type == "dolphin":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_dolphin_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads,
                sample_rate=16000, feature_dim=80, provider=self.device,
                decoding_method=self.decoding_method
            )

        elif model_type == "medasr":
            print(f"    - Initializing as MedASR CTC")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_medasr_ctc(
                model=model_file, 
                tokens=tokens, 
                num_threads=num_threads,
                provider=self.device, 
                decoding_method=self.decoding_method
            )

        elif model_type == "zipformer":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_zipformer_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads,
                sample_rate=16000, feature_dim=80, provider=self.device,
                decoding_method=self.decoding_method
            )

        elif model_type == "telespeech":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_telespeech_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads,
                sample_rate=16000, feature_dim=40, provider=self.device,
                decoding_method=self.decoding_method
            )

        elif model_type == "omnilingual":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads,
                provider=self.device, decoding_method=self.decoding_method
            )
            
        elif model_type == "tdnn":
            sr = 8000 if "yesno" in self.model_dir.lower() else 16000
            print(f"    - Sample Rate: {sr} (TDNN specific)")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_tdnn_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads,
                sample_rate=sr, feature_dim=23, provider=self.device,
                decoding_method=self.decoding_method
            )

        elif model_type == "wenet":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_wenet_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads,
                sample_rate=16000, feature_dim=80, provider=self.device
            )

        elif model_type == "paraformer":
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=model_file, tokens=tokens, num_threads=num_threads,
                sample_rate=16000, feature_dim=80, provider=self.device,
                decoding_method=self.decoding_method
            )

        else:
            print(f"    - [Fallback] Using Nemo CTC configuration")
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=model_file, tokens=tokens, num_threads=num_threads,
                sample_rate=16000, feature_dim=80, provider=self.device, 
                decoding_method=self.decoding_method
            )
            
        print(" --------------------------------------------------")

    def _run_dummy_check(self):
        print(">>> [Self-Check] Running sanity check...")
        try:
            dummy_audio = np.zeros(16000 * 2, dtype=np.float32) 
            s = self.recognizer.create_stream()
            s.accept_waveform(16000, dummy_audio)
            if self.is_streaming:
                while self.recognizer.is_ready(s):
                    self.recognizer.decode_stream(s)
            else:
                self.recognizer.decode_stream(s)
            print(">>> [Self-Check] Successful", flush=True)
        except Exception as e:
            print(f">>> [Self-Check] Error details: {e}", flush=True)
            raise e

    def create_stream(self):
        return self.recognizer.create_stream()

    def process_stream(self, stream):
        if self.is_streaming:
            while self.recognizer.is_ready(stream):
                self.recognizer.decode_stream(stream)
            result = self.recognizer.get_result(stream)
            if isinstance(result, str): return result
            elif hasattr(result, "text"): return result.text
            return str(result)
        else:
            self.recognizer.decode_stream(stream)
            if hasattr(stream, "result"): return stream.result.text
            result = self.recognizer.get_result(stream)
            if isinstance(result, str): return result
            elif hasattr(result, "text"): return result.text
            return str(result)