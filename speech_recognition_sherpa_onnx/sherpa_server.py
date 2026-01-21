import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from sobits_interfaces.action import SpeechRecognition
from ament_index_python.packages import get_package_share_directory

import numpy as np
import threading
import time
import os
import psutil
import asyncio
from concurrent.futures import ThreadPoolExecutor

from . import audio_utils
from . import vad
from . sherpa_core import SherpaEngine

class SherpaOnnxServer(Node):
    def __init__(self):
        super().__init__('sherpa_onnx_server', 
                         allow_undeclared_parameters=True, 
                         automatically_declare_parameters_from_overrides=True)

        def get_or_declare(name, default):
            if not self.has_parameter(name):
                self.declare_parameter(name, default)
            return self.get_parameter(name)

        self.model_name = get_or_declare('model_name', 'sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06').get_parameter_value().string_value
        self.min_wipe_duration = get_or_declare('min_wipe_duration', 0.2).get_parameter_value().double_value
        self.use_feedback_enabled = get_or_declare('use_feedback', True).get_parameter_value().bool_value
        self.extra_audio_duration = get_or_declare('extra_audio_duration_sec', 0.8).get_parameter_value().double_value
        self.max_speech_duration = get_or_declare('max_speech_duration', 30.0).get_parameter_value().double_value
        raw_device = get_or_declare('device', 'auto').get_parameter_value().string_value
        
        get_or_declare('vad_name', 'ten_vad')
        get_or_declare('hop_size', 256)
        get_or_declare('threshold', 0.5)

        self.use_echo_cancel = get_or_declare('use_echo_cancel', False).get_parameter_value().bool_value
        self.noise_suppression = get_or_declare('noise_suppression', False).get_parameter_value().bool_value
        self.analog_gain_control = get_or_declare('analog_gain_control', False).get_parameter_value().bool_value
        self.digital_gain_control = get_or_declare('digital_gain_control', False).get_parameter_value().bool_value

        if not self.has_parameter('mic_volume'):
            try:
                self.declare_parameter('mic_volume', '')
            except rclpy.exceptions.InvalidParameterTypeException:
                self.declare_parameter('mic_volume', 100)
        param_vol = self.get_parameter('mic_volume')

        mic_volume_raw = str(param_vol.value) if param_vol.value is not None else ""
        if mic_volume_raw.strip() != "" and mic_volume_raw.strip() != "None":
            self.mic_volume = mic_volume_raw if '%' in mic_volume_raw else f"{mic_volume_raw}%"
        else:
            self.mic_volume = ""

        self.source_to_modify = None
        self.original_mic_volume = None
        self.original_default_sink = None
        self.aec_module_index = None

        self.SOUND_FILES_PATH = os.path.join(get_package_share_directory('sobits_interfaces'), 'mp3')
        share_dir = get_package_share_directory('speech_recognition_sherpa_onnx')
        self.sound_file_directory = os.path.join(share_dir, 'sound_file')
        os.makedirs(self.sound_file_directory, exist_ok=True)

        try:
            audio_config = audio_utils.configure_pulseaudio(
                self.get_logger(), self.use_echo_cancel, self.noise_suppression,
                self.analog_gain_control, self.digital_gain_control, self.mic_volume
            )
            self.source_name = audio_config["source_name"]
            self.sample_rate = audio_config["sample_rate"]
            self.channels = audio_config["channels"]
            self.aec_module_index = audio_config["aec_module_index"]
            self.original_default_sink = audio_config["original_default_sink"]
            self.source_to_modify = audio_config["source_to_modify"]
            self.original_mic_volume = audio_config["original_mic_volume"]
            self.echo_cancel_source = audio_config["echo_cancel_source"]
            self.echo_cancel_sink = audio_config["echo_cancel_sink"]
            self.use_echo_cancel = audio_config["use_echo_cancel"]

            model_path = os.path.expanduser(os.path.join("~/.sherpa_onnx_asr_models/", self.model_name))
            self.device_name = SherpaEngine.determine_device(raw_device, self.get_logger())
            
            sherpa_config_dict = self._build_sherpa_config()
            
            self.engine = SherpaEngine(
                model_dir=model_path, 
                device=self.device_name,
                config=sherpa_config_dict 
            )
            self.get_logger().info(f"Model loaded: {self.model_name} for {self.device_name}")

            self.vad_processor = None
            self.chunk_size_bytes = 3200 
            if self.use_feedback_enabled:
                self.vad_processor = vad.VadProcessor(self)
                _, size, name = self.vad_processor.get_specs()
                self.chunk_size_bytes = size
                self.get_logger().info(f"VAD Initialized: {name}, chunk_size: {self.chunk_size_bytes}")

            self.action_server = ActionServer(
                self, SpeechRecognition, "speech_recognition",
                execute_callback=self.execute_callback,
                callback_group=ReentrantCallbackGroup(),
                goal_callback=self.goal_callback,
                cancel_callback=self.cancel_callback,
            )
            
            YELLOW = '\033[93m'
            ENDC = '\033[0m'
            self.get_logger().info(f"{YELLOW}Sherpa ONNX Server READY [{self.get_resources()}]{ENDC}")

        except Exception as e:
            self.get_logger().error(f"Initialization failed: {e}")
            self.cleanup()
            raise

    def _build_sherpa_config(self):
        config = {}

        def extract_prefix(prefix):
            params = self.get_parameters_by_prefix(prefix)
            section_dict = {}
            for key, param in params.items():
                parts = key.split('.')
                current = section_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = param.value
            return section_dict

        config['global_settings'] = extract_prefix('global_settings')
        config['streaming_models'] = extract_prefix('streaming_models')
        config['batch_models'] = extract_prefix('batch_models')
        return config

    def goal_callback(self, goal_request):
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info("Cancel request received")
        return CancelResponse.ACCEPT

    def get_resources(self):
        mem = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        return f"Mem: {mem:.1f}MB"

    async def execute_callback(self, goal_handle):
        audio_utils.cleanup_wav_files(self.sound_file_directory, self.get_logger())
        
        timeout_sec = goal_handle.request.timeout_sec
        silent = goal_handle.request.silent_mode
        feedback_rate = goal_handle.request.feedback_rate

        if timeout_sec < 0 and not self.use_feedback_enabled:
            goal_handle.abort()
            return SpeechRecognition.Result(result_text="Error: Infinite loop requires feedback mode.")

        feedback_executor = ThreadPoolExecutor(max_workers=1)
        capturer = audio_utils.AudioCapture(
            source_name=self.source_name, rate=self.sample_rate, channels=self.channels,
            chunk_size=self.chunk_size_bytes, 
            use_echo_cancel=self.use_echo_cancel, echo_cancel_source=self.echo_cancel_source
        )
        
        vad_segmenter = None
        if self.use_feedback_enabled:
            vad_segmenter = vad.VadSegmenter(
                self.vad_processor, self.min_wipe_duration, 
                self.max_speech_duration, self.extra_audio_duration
            )

        if not silent:
            t = threading.Thread(target=audio_utils.play_sound, args=('start_sound.mp3', self.SOUND_FILES_PATH, self.get_logger()))
            t.start()
            t.join()

        capturer.start()
        self.get_logger().info(f"Recording started. Timeout: {timeout_sec}s")

        all_audio_buffer = []
        start_time = time.time()
        response = SpeechRecognition.Result()
        recording_stopping = False
        audio_started = False
        file_counter = 0
        
        stream = self.engine.create_stream() 
        last_streaming_text = ""

        def run_inference_task(audio_data_list):
            if goal_handle.is_cancel_requested: return
            try:
                flat_int16 = np.concatenate(audio_data_list).astype(np.int16)
                samples = flat_int16.astype(np.float32) / 32768.0
                off_stream = self.engine.create_stream()
                off_stream.accept_waveform(16000, samples)
                text = self.engine.process_stream(off_stream)
                if text and not goal_handle.is_cancel_requested:
                    feedback = SpeechRecognition.Feedback()
                    feedback.addition_text = text.encode('utf-8', errors='ignore').decode('utf-8')
                    goal_handle.publish_feedback(feedback)
            except Exception as e:
                self.get_logger().error(f"Inference error: {e}")

        try:
            while rclpy.ok():
                if goal_handle.is_cancel_requested:
                    self.get_logger().info("Goal canceled during recording.")
                    capturer.stop()
                    feedback_executor.shutdown(wait=True)
                    goal_handle.canceled()
                    return response
                
                now = time.time()
                if not recording_stopping:
                    if audio_started and timeout_sec > 0 and now - start_time > timeout_sec:
                        capturer.stop(); recording_stopping = True
                    elif not audio_started and now - start_time > 10.0:
                        capturer.stop(); recording_stopping = True

                chunk = capturer.read()
                if chunk is None:
                    if not capturer.is_running: break
                    continue

                if not audio_started:
                    audio_started = True
                    start_time = time.time()
                    self.get_logger().info("Audio detection started.")

                resampled_data = np.frombuffer(chunk, dtype=np.int16)

                if timeout_sec >= 0:
                    all_audio_buffer.append(resampled_data)

                if self.engine.is_streaming:
                    samples = resampled_data.astype(np.float32) / 32768.0
                    stream.accept_waveform(16000, samples)
                    text = self.engine.process_stream(stream)
                    if text and text != last_streaming_text and self.use_feedback_enabled:
                        fb = SpeechRecognition.Feedback()
                        fb.addition_text = text
                        goal_handle.publish_feedback(fb)
                        last_streaming_text = text

                elif self.use_feedback_enabled and vad_segmenter:
                    segment = vad_segmenter.push_chunk(resampled_data, feedback_rate)
                    if segment is not None:
                        feedback_executor.submit(run_inference_task, segment)
                        file_counter += 1
                        path = os.path.join(self.sound_file_directory, f'feedback_{file_counter}.wav')
                        flat_save = np.concatenate(segment).astype(np.int16)
                        feedback_executor.submit(lambda d, p: audio_utils.save_buffer_to_wav(d, p, 16000, 1, self.get_logger()), flat_save, path)

        finally:
            capturer.stop()
            feedback_executor.shutdown(wait=True)

        if not silent:
            threading.Thread(target=audio_utils.play_sound, args=('end_sound.mp3', self.SOUND_FILES_PATH, self.get_logger())).start()

        final_text = ""
        if self.engine.is_streaming:
            final_text = self.engine.process_stream(stream)
        elif all_audio_buffer and timeout_sec >= 0:
            full_audio = np.concatenate(all_audio_buffer).astype(np.int16)
            samples = full_audio.astype(np.float32) / 32768.0
            full_stream = self.engine.create_stream()
            full_stream.accept_waveform(16000, samples)
            final_text = self.engine.process_stream(full_stream)
            p = os.path.join(self.sound_file_directory, "final_output.wav")
            audio_utils.save_buffer_to_wav(full_audio, p, 16000, 1, self.get_logger())
        
        response.result_text = final_text if final_text else "No speech recognized."
        self.get_logger().info(f"[{self.get_resources()}]")
        goal_handle.succeed()
        return response

    def cleanup(self):
        source = getattr(self, 'source_to_modify', None)
        vol = getattr(self, 'mic_volume', "")
        orig_vol = getattr(self, 'original_mic_volume', None)
        sink = getattr(self, 'original_default_sink', None)
        aec = getattr(self, 'aec_module_index', None)
        audio_utils.cleanup_pulse_audio(self.get_logger(), source, vol, orig_vol, sink, aec)

def main(args=None):
    rclpy.init(args=args)
    sherpa_onnx_server = None
    try:
        sherpa_onnx_server = SherpaOnnxServer()
        executor = MultiThreadedExecutor()
        executor.add_node(sherpa_onnx_server)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if sherpa_onnx_server is not None:
            sherpa_onnx_server.cleanup()
            sherpa_onnx_server.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()