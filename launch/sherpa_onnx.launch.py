import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'speech_recognition_sherpa_onnx'

    stt_engine_arg = DeclareLaunchArgument(
        'stt_engine',
        default_value='sherpa',
        description='STT Engine type (e.g., sherpa)'
    )

    model_name_arg = DeclareLaunchArgument(
        'model_name',
        default_value='sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06',
        description='Name of the model folder'
    )

    default_config_path = os.path.join(
        get_package_share_directory(package_name),
        'config',
        'params.yaml'
    )

    device_arg = DeclareLaunchArgument(
        'device',
        default_value='cpu',
        description='Execution device (cpu, cuda, coreml)'
    )

    mic_volume_arg = DeclareLaunchArgument(
        'mic_volume',
        default_value='',
        description='Microphone volume level'
    )

    use_feedback_arg = DeclareLaunchArgument(
        'use_feedback',
        default_value='true',
        description='Whether to use audio feedback'
    )

    vad_name_arg = DeclareLaunchArgument(
        'vad_name',
        default_value='ten_vad',
        description='VAD model name'
    )

    hop_size_arg = DeclareLaunchArgument(
        'hop_size',
        default_value='256',
        description='Hop size for audio processing'
    )

    threshold_arg = DeclareLaunchArgument(
        'threshold',
        default_value='0.5',
        description='VAD threshold value'
    )

    min_wipe_duration_arg = DeclareLaunchArgument(
        'min_wipe_duration',
        default_value='0.2',
        description='Minimum duration to wipe audio buffer'
    )

    extra_audio_duration_sec_arg = DeclareLaunchArgument(
        'extra_audio_duration_sec',
        default_value='0.8',
        description='Extra audio duration in seconds'
    )

    max_speech_duration_arg = DeclareLaunchArgument(
        'max_speech_duration',
        default_value='30.0',
        description='Maximum speech duration in seconds'
    )

    use_echo_cancel_arg = DeclareLaunchArgument(
        'use_echo_cancel',
        default_value='false',
        description='Whether to use echo cancellation'
    )

    noise_suppression_arg = DeclareLaunchArgument(
        'noise_suppression',
        default_value='false',
        description='Whether to use noise suppression'
    )

    analog_gain_control_arg = DeclareLaunchArgument(
        'analog_gain_control',
        default_value='false',
        description='Analog Gain Control'
    )

    digital_gain_control_arg = DeclareLaunchArgument(
        'digital_gain_control',
        default_value='false',
        description='Digital Gain Control'
    )

    config_path_arg = DeclareLaunchArgument(
        'config_path',
        default_value=default_config_path,
        description='Full path to the YAML configuration file'
    )

    sherpa_onnx_node = Node(
        package=package_name,
        executable='sherpa_server',
        name='sherpa_onnx_server',
        output='screen',
        parameters=[
            LaunchConfiguration('config_path'),
            {
                'config_path': LaunchConfiguration('config_path'),
                'stt_engine': LaunchConfiguration('stt_engine'),
                'model_name': LaunchConfiguration('model_name'),
                'device': LaunchConfiguration('device'),
                'mic_volume': LaunchConfiguration('mic_volume'),
                'use_feedback': LaunchConfiguration('use_feedback'),
                'vad_name': LaunchConfiguration('vad_name'),
                'hop_size': LaunchConfiguration('hop_size'),
                'threshold': LaunchConfiguration('threshold'),
                'min_wipe_duration': LaunchConfiguration('min_wipe_duration'),
                'extra_audio_duration_sec': LaunchConfiguration('extra_audio_duration_sec'),
                'max_speech_duration': LaunchConfiguration('max_speech_duration'),
                'use_echo_cancel': LaunchConfiguration('use_echo_cancel'),
                'noise_suppression': LaunchConfiguration('noise_suppression'),
                'analog_gain_control': LaunchConfiguration('analog_gain_control'),
                'digital_gain_control': LaunchConfiguration('digital_gain_control'),
            }
        ]
    )

    return LaunchDescription([
        config_path_arg,
        stt_engine_arg,
        model_name_arg,
        device_arg,
        mic_volume_arg,
        use_feedback_arg,
        vad_name_arg,
        hop_size_arg,
        threshold_arg,
        min_wipe_duration_arg,
        extra_audio_duration_sec_arg,
        max_speech_duration_arg,
        use_echo_cancel_arg,
        noise_suppression_arg,
        analog_gain_control_arg,
        digital_gain_control_arg,
        sherpa_onnx_node
    ])