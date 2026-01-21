<a name="readme-top"></a>

[JA](README.md) | [EN](README.en.md)

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

# Speech Recognition Sherpa Onnx

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#introduction">Introduction</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#launch-and-usage">Launch and Usage</a></li>
    <li><a href="#model-download-method">Model Download Method</a></li>
    <li>
      <a href="#パラメータ">パラメータ</a>
      <ul>
        <li><a href="#parameters-configurable-in-the-launch-file">Parameters Configurable in the Launch File</a></li>
        <li><a href="#parameters-configurable-in-the-yaml-file">Parameters Configurable in the YAML File</a></li>
      </ul>
    </li>
    <li><a href="#milestone">Milestone</a></li>
    <li><a href="#references">References</a></li>
  </ol>
</details>

## Introduction

Speech Recognition Sherpa Onnx is a ROS 2 package designed to provide speech recognition capabilities via Action communication, leveraging the [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) engine powered by ONNX Runtime.

It is optimized for CPU environments and supports both streaming (real-time) and batch recognition across a wide variety of available models.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started
This section describes how to set up this repository.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Prerequisites
First, please set up the following environment before proceeding to the next installation stage.

| System  | Version |
| --- | --- |
| Ubuntu | 22.04 (Jammy Jellyfish) |
| ROS    | Humble Hawksbill |
| Python | 3.10 |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Installation
1. Go to the `src` folder of ROS2.
    ```sh
    cd ~/colcon_ws/src/
    ```

2. Clone this repository.
    ```sh
    git clone -b humble-devel https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx.git
    ```
3. Navigate into the repository.
    ```sh
    cd speech_recognition_sherpa_onnx/
    ```
4. Install the dependent packages. 
    ```sh
    bash install.sh
    ```
5. Compile the package.
    ```sh
    cd ~/colcon_ws/
    ```
    ```sh
    colcon build --symlink-install
    ```
    ```sh
    source ~/colcon_ws/install/setup.sh
    ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Launch and Usage
1. Follow the [Model Download Method](https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx%3Ftab%3Dreadme-ov-file%23%25E3%2583%25A2%25E3%2583%2587%25E3%2583%25AB%25E3%2581%25AE%25E3%2583%2580%25E3%2582%25A6%25E3%2583%25B3%25E3%2583%25AD%25E3%2583%25BC%25E3%2583%2589%25E6%2596%25B9%25E6%25B3%2595) to download the models used for speech recognition.

2. In Ubuntu settings, set the input device for sound to the microphone you intend to use.

3. Copy the name of the model you wish to use from the list displayed by the following command:
    ```sh
    ls ~/.sherpa_onnx_asr_models/
    ```

4. Update the `model_name` in [sherpa_onnx.launch.py](launch/sherpa_onnx.launch.py) to match your chosen model, then launch it using the following command. Please wait until `Sherpa Onnx Server is READY and waiting for requests` is displayed before sending any goals.

   ```sh
   ros2 launch speech_recognition_sherpa_onnx sherpa_onnx.launch.py 
   ```

5. Start the Action Client.
    - timeout_sec: Duration (in seconds) to keep the microphone open. If a negative value is provided, it continues to return feedback until a cancel request is sent.
    - silent_mode: When set to `true`, sound feedback is disabled at the start of detection and upon termination.
    - feedback_rate: The frequency at which intermediate speech recognition results are returned when `use_feedback` is set to `True` and `vad_name` is set to `None`. (Measured in seconds, e.g., 0.5 means every 0.5 seconds.)
    ```sh
    ros2 action send_goal /speech_recognition sobits_interfaces/action/SpeechRecognition "timeout_sec: 5 
    silent_mode: false
    feedback_rate: 0.5" -f
    ```

    Recorded audio is saved in the **sound_file** directory.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Model Download Method
1. Launch the GUI using the following command:
    ```sh
    ros2 run speech_recognition_sherpa_onnx model_downloader
    ```
  - After launching, the following will be displayed:
  ![img](img/gui.png)
      - Recommended
        - Displays recommended models.
      - Search (GitHub)
        - Fetches and displays currently available models from GitHub.
        - You can filter models by specifying up to three keywords.
        - Models that may not work in your PC environment are displayed in red.
      - Installed Models
        - Displays a list of installed models.
        - Installed models can be removed using the "Delete Selected" button.
    
    <details>
    <summary><b>About Model Selection</b></summary>

    - Model performance and resource requirements vary depending on size and execution environment. Please use the following as a general guideline:
    - Streaming Models: Designed for real-time, sequential processing of audio data.
        - transducer
            - Primarily intended for streaming. While usable for offline inference, it is optimized for real-time recognition.
        - wenet_ctc
            - Known for stable operation; frequently adopted for industrial applications.
        - zipformer2_ctc
            - Offers low latency and high efficiency, making it suitable for streaming (also usable offline).
        - paraformer
            - Designed for low-latency, high-speed operation. Its lightweight configuration makes it suitable for embedded systems.
        - nemo_ctc
            - Demonstrates high recognition performance, but can be heavier than other lightweight models on CPU (often intended for GPU environments).
        - t_one_ctc
            - A model aimed at an extremely lightweight configuration. Effective for environments where CPU resources need to be conserved.

    - Batch Models: Designed for processing entire audio segments at once.
        - whisper
            - High accuracy and multilingual support. Includes translation features, but has a higher computational load (GPU is recommended for larger models).
        - sense_voice
            - A multi-functional model capable of transcription with additional features like emotion detection and ITN (Inverse Text Normalization).
        - nemo_canary
            - A series of models providing multilingual recognition and high-precision translation capabilities.
        - transducer
            - Primarily for streaming, but also supports offline processing.
        - moonshine
            - A model offering a good balance between accuracy and speed.
        - fire_red_asr
            - Offers high accuracy but tends to have high memory consumption.
        - paraformer
            - Capable of batch processing and can be configured to run fast even in environments with limited computational resources.
        - zipformer
            - Features an efficient, low-latency architecture; suitable for both streaming and offline use.
        - dolphin
            - A versatile model designed for low memory usage while supporting multiple languages.
        - medasr
            - Optimized for dictation tasks involving medical terminology.
        - telespeech
            - Trained on large-scale datasets; demonstrates high accuracy, particularly in languages like Chinese.
        - omnilingual
            - A multilingual ASR model aimed at supporting a vast number of languages (over 1,600).
        - tdnn
            - A classic, lightweight neural architecture (TDNN-based). Widely used as a foundation for ASR.
        - wenet
            - Characterized by stable operation and frequently applied in industrial settings.
        - nemo
            - Provides high recognition accuracy, though processing speed and resource requirements depend on model size and execution environment.
        - fun_asr_nano
            - Support for ultra-small models combined with LLMs is planned (scheduled in the roadmap/milestones).
  
      
      </details>

2. Click on a model to select it.
3. Click the Download button to download and extract the model.
4. Once completed, click Close to exit the window.

- You can also browse the full list of available models [here](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models).
- You can verify the list of installed models using the following command:
    ```sh
    ls ~/.sherpa_onnx_asr_models/
    ```



<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Parameters
There are two types of parameters: those that can be configured in [sherpa_onnx.launch.py](launch/sherpa_onnx.launch.py).launch.py and those that can be configured in [params.yaml](config/params.yaml).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Parameters Configurable in the Launch File

In [sherpa_onnx.launch.py](launch/sherpa_onnx.launch.py), you can specify the following parameters:

| Parameter | Description | Default Value |
| --- | --- | --- |
| model_name | Name of the speech recognition model | sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06 |
| device | Computing device to use. Currently, only `cpu` is supported. | cpu |
| mic_volume | Sets the microphone input volume as a percentage. It returns to the original volume after the program exits. Example: "150" | "" |
| use_feedback | Whether to use Feedback. | True |


---

The following are parameters related to Feedback.
They are only effective when `use_feedback` is set to `True`.
Changing these values will not affect the final recognition result.

| Parameter | Description | Default Value |
| --- | --- | --- |
| vad_name | The Voice Activity Detection (VAD) method used for feedback. Using VAD improves the recognition accuracy of feedback. If you select None, VAD will not be used and speech recognition will be performed at the Feedback Rate specified by the Action Client. | ten_vad |
| hop_size | The size of the chunk (fragment) of audio data processed by the VAD model. You can select 160 or 256. A smaller value increases responsiveness but also increases CPU load. | 256 |
| threshold | The probability threshold for the VAD model to detect speech. A higher value reduces false positives, but quiet or faint voices may be ignored. | 0.5 |
| min_wipe_duration | The minimum required duration of a voice to be processed for speech recognition, ignoring noise. If a section recognized as speech by VAD is shorter than this duration, it will be ignored as noise and not processed for speech recognition. | 0.2 |
| extra_audio_duration_sec | Additional audio time to include before and after the audio for each feedback. | 0.2 |
| max_speech_duration | Maximum duration (in seconds) to segment a single utterance. | 30.0 |


---
The following are parameters related to echo cancellation.

| Parameter | Description |	Default Value|
| --- | --- | --- |
| use_echo_cancel | It helps prevent the microphone from picking up audio from the speakers. | False |
| noise_suppression | Toggles the noise suppression feature. | False |
| analog_gain_control | Automatically adjusts the microphone input volume at the hardware level. It suppresses loud sounds and amplifies quiet ones to prevent clipping and improve clarity. | False |
| digital_gain_control | Automatically adjusts the input volume at the software level. It modifies the amplitude after the audio data has been digitized. | False |

- Parameters other than `model_name`, `use_feedback`, `vad_name`, and those related to echo cancellation can be changed after the launch file is started.
    - Example: To change `min_wipe_duration` to 0.1
    ```sh
    ros2 param set /sherpa_onnx_server min_wipe_duration 0.1
    ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Parameters Configurable in the YAML File

In [params.yaml](config/params.yaml), you can specify the following parameters for each model type.

- `global_settings`: A set of parameters common to all models.

    | Parameter | Description | Default Value |
    | --- | --- | --- |
    | decoding_method | Search algorithm: `greedy_search` or `modified_beam_search` | greedy_search |

    - `greedy_search`: A speed-priority mode that selects the single most probable candidate. It has low overhead and fast response times, though accuracy may be slightly lower.

    - `modified_beam_search`: An accuracy-priority mode that explores multiple candidates in parallel. It enables more precise recognition based on context but increases CPU load.

- `streaming_models`: Models designed for real-time, sequential processing of audio.

    <details>
    <summary><b>Streaming Model Parameters</b></summary>

    - The following parameters are common to all streaming models.

    | Parameter | Description and Impact of Adjustment | Default |
    | --- | --- | --- |
    | enable_endpoint_detection | Enables automatic segmentation via silence detection. When `true`, it automatically detects the end of an utterance. | false |
    | rule1_min_trailing_silence | Minimum silence duration (in seconds) to trigger an endpoint before speech. Lowering this speeds up detection but makes it more susceptible to noise. | 2.4 |
    | rule2_min_trailing_silence | Minimum silence duration (in seconds) to trigger an endpoint during speech. Lowering this confirms recognition faster but may cause premature cuts during pauses. | 1.2 |
    | rule3_min_utterance_length | Maximum utterance duration (in seconds). When exceeded, the recognition is forcibly finalized and segmented. | 20.0 |


    * The following parameters can be configured individually for each model type.
        * `num_threads` can be set per model category:

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | num_threads | Number of CPU threads used for inference. Increasing this speeds up processing but raises CPU load. | 2 |
    
    * `transducer`

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | max_active_paths | The number of candidate paths to explore. Increasing this improves accuracy but increases computational cost. | 4 |
        | blank_penalty | Penalty for silence. Increasing this encourages the model to output characters more aggressively. | 0.0 |
        | temperature_scale | Adjusts prediction diversity. Higher values make the model more likely to select high-confidence results. | 2.0 |
    
    * `wenet_ctc`

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | chunk_size | The unit of processing (number of frames). Smaller values reduce latency but may decrease contextual understanding. | 16 |
        | num_left_chunks | The amount of past data to reference. Increasing this stabilizes accuracy at the cost of higher computational load. | 4 |

    * `zipformer2_ctc`

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | ctc_max_active | Maximum number of states to maintain during CTC decoding. Larger values result in more precise calculations. | 3000 |
    * For `paraformer`, `nemo_ctc`, and `t_one_ctc`, the only configurable individual parameter is `num_threads`.


    </details>

* `batch_models`: Models designed for processing entire audio segments at once.

    <details>
    <summary><b>Parameters for Each Batch Model Type</b></summary>
        
    * The following parameters can be configured individually for each model type.
    * `num_threads` can be set per model category:

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | num_threads | Number of CPU threads used for inference. Increasing this speeds up processing but raises CPU load. | 2 |


    * `whisper`

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | language | The target language for recognition (e.g., `ja`, `en`). `auto` (auto-detect) is also available. | "en" |
        | task | Task type: `transcribe` or `translate`. | "transcribe" |
        | tail_paddings | Number of padding frames at the end of the audio. -1 automatically uses the model's optimal value. | -1 |


    * `sense_voice`

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | language | Target language: `auto`, `zh`, `en`, `ja`, `ko`, etc. | "auto" |
        | use_itn | Whether to format numbers and symbols for better readability (Inverse Text Normalization). | true |


    * `nemo_canary`

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | src_lang | Language of the input audio. | "en" |
        | tgt_lang | Language of the output text. | "en" |


    * `transducer`

        | Parameter | Description | Default Value |
        | --- | --- | --- |
        | max_active_paths | Number of candidate paths to explore. Increasing this improves accuracy but increases computational cost. | 4 |
        | blank_penalty | Penalty for silence. Increasing this encourages the model to output characters more aggressively. | 0.0 |


    * For `moonshine`, `fire_red_asr`, `paraformer`, `zipformer`, `dolphin`, `medasr`, `telespeech`, `omnilingual`, `tdnn`, `wenet`, and `nemo`, the only configurable individual parameter is `num_threads`.




    </details>


<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Milestone
- [ ] Support for `fun_asr_nano`

See the [open issues][issues-url] for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## References
* [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
* [TEN VAD](https://github.com/TEN-framework/ten-vad)
* [module-echo-cancel](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Modules/?utm_source=chatgpt.com#module-echo-cancel)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/TeamSOBITS/speech_recognition_sherpa_onnx.svg?style=for-the-badge
[contributors-url]: https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/TeamSOBITS/speech_recognition_sherpa_onnx.svg?style=for-the-badge
[forks-url]: https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx/network/members
[stars-shield]: https://img.shields.io/github/stars/TeamSOBITS/speech_recognition_sherpa_onnx.svg?style=for-the-badge
[stars-url]: https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx/stargazers
[issues-shield]: https://img.shields.io/github/issues/TeamSOBITS/speech_recognition_sherpa_onnx.svg?style=for-the-badge
[issues-url]: https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx/issues
[license-shield]: https://img.shields.io/github/license/TeamSOBITS/speech_recognition_sherpa_onnx.svg?style=for-the-badge
[license-url]: LICENSE