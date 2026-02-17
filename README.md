<a name="readme-top"></a>

[JA](README.md) | [EN](README.en.md)

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]

# Speech Recognition Sherpa ONNX

<!-- 目次 -->
<details>
  <summary>目次</summary>
  <ol>
    <li>
      <a href="#概要">概要</a>
    </li>
    <li>
      <a href="#セットアップ">セットアップ</a>
      <ul>
        <li><a href="#環境条件">環境条件</a></li>
        <li><a href="#インストール方法">インストール方法</a></li>
      </ul>
    </li>
    <li><a href="#実行操作方法">実行・操作方法</a></li>
    <li><a href="#モデルのダウンロード方法">モデルのダウンロード方法</a></li>
    <li>
      <a href="#パラメータ">パラメータ</a>
      <ul>
        <li><a href="#launchファイルで設定可能なパラメータ">Launchファイルで設定可能なパラメータ</a></li>
        <li><a href="#yamlファイルで設定可能なパラメータ">YAMLファイルで設定可能なパラメータ</a></li>
      </ul>
    </li>
    <li><a href="#マイルストーン">マイルストーン</a></li>
    <li><a href="#参考文献">参考文献</a></li>
  </ol>
</details>

## 概要

Speech Recognition Sherpa ONNXは，ONNX Runtimeを活用した音声認識エンジン [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) をROS 2 のAction通信で利用するためのパッケージです．

CPU環境で動作します．また，ストリーミング認識（逐次認識）とバッチ認識（一括認識）の両方に対応しており，膨大なモデル群から様々なモデルを選択できます．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

## セットアップ
ここで，本レポジトリのセットアップ方法について説明します．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

### 環境条件
まず，以下の環境を整えてから，次のインストール方法に進んでください．
| System  | Version |
| --- | --- |
| Ubuntu | 22.04 (Jammy Jellyfish) |
| ROS    | Humble Hawksbill |
| Python | 3.10 |

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

### インストール方法
1. ROS2の`src`フォルダに移動します．
    ```sh
    cd ~/colcon_ws/src/
    ```

2. 本レポジトリをcloneします．
    ```sh
    git clone -b humble-devel https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx.git
    ```
3. レポジトリの中へ移動します．
    ```sh
    cd speech_recognition_sherpa_onnx/
    ```
4. 依存パッケージをインストールします．時間がかかるので注意．
    ```sh
    bash install.sh
    ```
5. パッケージをコンパイルします．
    ```sh
    cd ~/colcon_ws/
    ```
    ```sh
    colcon build --symlink-install
    ```
    ```sh
    source ~/colcon_ws/install/setup.sh
    ```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

## 実行・操作方法
1. [モデルダウンロード方法](https://github.com/TeamSOBITS/speech_recognition_sherpa_onnx?tab=readme-ov-file#%E3%83%A2%E3%83%87%E3%83%AB%E3%81%AE%E3%83%80%E3%82%A6%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%89%E6%96%B9%E6%B3%95)を参考に音声認識に使用するモデルをダウンロードします．

2. Ubuntuの設定で，サウンドの入力デバイスを使用するマイクに設定します．

3. 以下のコマンドで表示されたモデルの中から，使用したいモデル名をコピーします．
    ```sh
    ls ~/.sherpa_onnx_asr_models/
    ```

4. [sherpa_onnx.launch.py](launch/sherpa_onnx.launch.py)の``model_name``を使用するモデル名に書き換えてから，以下のコマンドで起動します．**Sherpa Onnx Server is READY and waiting for requests**と表示されるまでgoalを送らずに待機してください．

   ```sh
   ros2 launch speech_recognition_sherpa_onnx sherpa_onnx.launch.py 
   ```

5. アクションクライアントを起動します．
  - timeout_sec: マイクを開く秒数．負の値のときキャンセルを送信するまでフィードバックを返し続ける．
  - silent_mode: trueのときは検出時と終了時に音がならない．
  - feedback_rate: `use_feedback`が`True`で`vad_name`が`None`のときに返ってくる途中の音声認識結果の頻度．
    ```sh
    ros2 action send_goal /speech_recognition sobits_interfaces/action/SpeechRecognition "timeout_sec: 5 
    silent_mode: false
    feedback_rate: 0.5" -f
    ```

  録音された音声は**sound_file**ディレクトリに保存されます．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

## モデルのダウンロード方法
1. 以下のコマンドでGUIを起動します．
    ```sh
    ros2 run speech_recognition_sherpa_onnx model_downloader
    ```
  - 起動後は以下が表示されます．
  ![img](img/gui.png)
      - Recommended
        - おすすめのモデルを表示します．
      - Search (GitHub)
        - 現在利用可能なモデルをGitHubから取得し表示します．
        - Keywordを3つまで指定してモデル名の絞り込み検索ができます．
        - PC環境で動作しない可能性があるモデルは赤色で表示されます．
      - Installed Models
        - インストール済みのモデル一覧を表示します．
        - インストール済みのモデルはDelete Selectedボタンで削除できます．
    
    <details>
    <summary><b>モデル選定について</b></summary>


    - モデルの性能・リソース要件はサイズや実行環境によって変わります．以下は参考程度にしてください．
    - ストリーミングモデル：音声をリアルタイムで逐次処理するモデルです
      - transducer
        - ストリーミングを主用途とするモデル．オフライン推論にも利用可能だが，主にリアルタイム認識向け．
      - wenet_ctc
        - 安定動作が特徴で，産業用途でも採用されることが多い．
      - zipformer2_ctc
        - 低遅延かつ効率的で，ストリーミング用途に適する（オフラインでも利用可能）．
      - paraformer
        - 低レイテンシで高速に動作する設計．軽量構成も可能で組込み用途にも向く．
      - nemo_ctc
        - 高い認識性能を示すが，特にCPU環境では他の軽量モデルより重くなることがある（GPU環境での利用が想定されることが多い）．
      - t_one_ctc 
        - 非常に軽量な構成を目指したモデル．CPUリソースを節約したい環境に有効．

    - バッチモデル：音声をまとめて処理するモデルです
      - whisper
        - 高精度かつ多言語対応．翻訳機能も備えるが計算負荷は高め（特に大きなモデルはGPU推奨）．
      - sense_voice
        - 感情検知やITN（数値整形）などの付加機能を持ち，多機能な書き起こしが可能．
      - nemo_canary
        - 多言語認識および高精度な翻訳機能を提供するモデル群．
      - transducer
        - ストリーミングを主用途とするが，オフライン処理にも利用可能（両対応）．
      - moonshine
        - 精度と速度のバランスが良いモデル．
      - fire_red_asr
        - 精度は高いがメモリ消費量が大きい傾向にある．
      - paraformer
        - バッチでも動作可能で，計算リソースが限られた環境でも高速に動作する構成が可能．
      - zipformer
        - 効率的で低遅延な構造を持ち，ストリーミング／オフラインの両方で利用可能．
      - dolphin
        - 省メモリで複数言語に対応することを目指した汎用モデル．
      - medasr
        -  医療用語を含む口述作業に適しています．
      - telespeech
        - 大規模データで学習されており，特に中国語などで高い精度を示すことがある．
      - omnilingual
        - 多数の言語(1600以上)に対応することを目的とした多言語ASRモデル．
      - tdnn
        - 古典的かつ軽量なニューラル構造（TDNN系）．ASRの基盤として広く用いられる（特定のタスク専用ではない）．
      - wenet
        - 安定した動作が特徴で，産業用途にも適用されることが多い．
      - nemo
        - 高精度な認識を示すが，処理速度やリソース要件はモデルのサイズや実行環境に依存する．
      - fun_asr_nano
        - LLMを組み合わせた超小型モデル．プロンプトを指定可能．
      
      
      </details>

2. モデルをクリックして選択します．
3. Downlaodボタンを押してモデルをダウンロードし展開します．
4. 完了したらCloseをクリックして閉じます．

- すべてのモデルは[こちら](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models)でも確認できます．

- インストール済みのモデル一覧は以下のコマンドでも確認できます．
    ```sh
    ls ~/.sherpa_onnx_asr_models/
    ```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

## パラメータ
パラメータは[sherpaserver.launch.py](launch/sherpaserver.launch.py)で設定可能なものと，[params.yaml](config/params.yaml)で設定可能なものの2種類があります．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

### Launchファイルで設定可能なパラメータ
[sherpaserver.launch.py](launch/sherpaserver.launch.py)では以下のパラメータを指定できます．

| パラメータ | 説明 | デフォルト値 |
| --- | --- | --- |
| model_name | 音声認識モデルの名前| sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06 |
| device | 使用する計算デバイス． 現在は`cpu`のみに対応| cpu |
| mic_volume	| マイクの入力音量をパーセンテージで設定する．プログラム終了後は元の音量に戻る．例: "150" | "" |
| use_feedback | Feedbackを使用するかどうか | True |


---
以下はFeedbackに関するパラメータです．
`use_feedback`が`True`のときのみ有効です．
以下の値を変更しても最終認識結果には影響しません．

| パラメータ | 説明 | デフォルト値 |
| --- | --- | --- |
| vad_name | フィードバックの際に使用する音声アクティビティ検出(VAD)の手法．VADの使用によりフィードバックの認識精度が向上する．Noneを選択するとVADを使用せずAction Clientで指定したFeedback Rateの秒数ごとに音声認識を行う． | ten_vad |
| hop_size | VADモデルが音声データを処理するチャンク（断片）のサイズ．160 or 256を選択可能．値が小さいほど応答性が上がるが，CPU負荷が増える | 256 |
| threshold | VADモデルが音声を検出するための確率のしきい値．値を高くすると誤検出が減るが，かすれた声や小さな声が無視される可能性がある | 0.5 |
| min_wipe_duration | ノイズを無視し音声認識するために必要な声の最短の長さ．VADが発話と認識した区間がこの秒数より短い場合，ノイズとして無視され音声認識の処理を行わない． | 0.2 |
| extra_audio_duration_sec | フィードバックごとに音声の前後に含める追加のオーディオ時間 | 0.2 | 
| max_speech_duration | 1回の発話を区切る最大秒数．	 | 30.0 | 


---
以下はエコーキャンセルに関するパラメータです． `use_echo_cancel`が`True`のときに有効です．

| パラメータ | 説明 | デフォルト値 |
| --- | --- | --- |
| use_echo_cancel | エコーキャンセルを使用するかどうか | False |
| noise_suppression | ノイズを抑制する．| False |
| analog_gain_control | マイクのハードウェアレベルで入力音量を自動調整する．大きな音は抑え，小さな音は増幅することで音割れや聞き取りにくさを防ぐ． | False |
| digital_gain_control | マイクのソフトウェアレベルで入力音量を自動調整する． | False |

- `model_name`, `use_feedback`, `vad_name`とエコーキャンセル関連以外のパラメータはlaunchファイル起動後でも変更可能です．
  - 例：`min_wipe_duration`を0.1に変更する場合
    ```sh
    ros2 param set /sherpa_onnx_server min_wipe_duration 0.1
    ```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

### YAMLファイルで設定可能なパラメータ
[params.yaml](config/params.yaml)ではモデルの種類ごとに以下のパラメータを指定できます．

- `global_settings`：全モデル共通のパラメータ群です．

  | パラメータ | 説明 | デフォルト値 |
  | --- | --- | --- |
  | decoding_method | 探索アルゴリズム．`greedy_search` or `modified_beam_search` | greedy_search |
  
    - `greedy_search`: 最も確率の高い候補を1つ選ぶ速度優先モード．低負荷でレスポンスが早いが，精度はやや落ちる．
    - `modified_beam_search`: 複数の候補を並行して探索する精度優先モード．文脈に沿った正確な認識が可能だが，CPU負荷が増える．

- `streaming_models`: 音声をリアルタイムで逐次処理するモデルです．

  <details>
  <summary><b>ストリーミングモデルのパラメータ</b></summary>

  - 以下はストリーミングモデルで共通のパラメータです．

    | パラメータ | 説明と調整の影響 | デフォルト |
    | --- | --- | --- |
    | enable_endpoint_detection | 無音検知による自動区切りの有効化．`true` で発話終了を自動判別． | false |
    | rule1_min_trailing_silence | 発話前の無音判定秒数．値を下げると開始判定が早まるが，ノイズに弱くなる． | 2.4 |
    | rule2_min_trailing_silence | 発話中の区切り秒数．値を下げると認識が早く確定するが，言葉の間で途切れやすくなる． | 1.2 |
    | rule3_min_utterance_length | 最大継続秒数．この値を超えると強制的に認識を確定し，分割する． | 20.0 |
  
  - 以下はモデルごとに個別で設定可能なパラメータです．
    - `num_threads`はモデル種類ごとに設定可能です
      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | num_threads | 推論に使用するCPUスレッド数．上げると処理が早くなるが，CPU負荷が増大する． | 2 |
    - `transducer`

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | max_active_paths | 探索する候補の数．値を増やすと精度が上がるが，処理が重くなる．| 4 |
      | blank_penalty | 無音に対するペナルティ．値を上げると，より積極的に文字を出そうとする．| 0.0 |
      | temperature_scale | 予測の多様性の調整．値を上げると自信のある結果が選ばれやすくなる．　| 2.0 |

    - `wenet_ctc`

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | chunk_size | 処理の単位（フレーム数）．小さいほど低遅延になるが，文脈の理解度が下がる．| 16 |
      | num_left_chunks | 過去のデータをどれだけ参照するか．増やすと精度が安定するが計算負荷が増える．| 4 |

    - `zipformer2_ctc`

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | ctc_max_active |　CTCデコード時に保持する最大状態数．大きいほど計算が精密になる． | 3000|

    - `paraformer`, `nemo_ctc`, `t_one_ctc`に設定できる個別パラメータは`num_threads`のみです．
  
  </details>

---
- `batch_models`: 音声をまとめて処理するモデルです．

  <details>
  <summary><b>バッチモデルの種類ごとのパラメータ</b></summary>
  
  - 以下はモデルごとに個別で設定可能なパラメータです．
    - `num_threads`はモデル種類ごとに設定可能です．

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | num_threads | 推論に使用するCPUスレッド数．上げると処理が早くなるが，CPU負荷が増大する． | 2 |

    - `whisper`

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | language | 認識対象の言語（`ja`, `en`等）．`auto`（自動判別）も指定可能．| "en" |
      | task | 処理内容．`transcribe` or `translate`| "transcribe" |
      | tail_paddings | 音声末尾のパディング数．-1 はモデルの最適値を自動使用．| -1 |
    
    - `sense_voice`

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | language | 対象言語．`auto`, `zh`, `en`, `ja`, `ko` 等が指定可能 | "auto" |
      | use_itn | 数値や記号を読みやすく整形するか | true |
    
    - `nemo_canary`

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | src_lang | 入力音声の言語．| "en" |
      | tgt_lang | 出力テキストの言語 | "en" |

    - `transducer`

      | パラメータ | 説明 | デフォルト値 |
      | --- | --- | --- |
      | max_active_paths | 探索する候補の数．値を増やすと精度が上がるが，処理が重くなる． | 4 |
      | blank_penalty | 無音に対するペナルティ．値を上げると，より積極的に文字を出そうとする． | 0.0 |

    - `moonshine`,  `fire_red_asr`, `paraformer`, `zipformer`, `dolphin`, 
        `medasr`, `telespeech`, `omnilingual`, `tdnn`, `wenet`, `nemo`に設定できる個別パラメータは`num_threads`のみです．
      
  </details>

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

  ## マイルストーン

現時点のバッグや新規機能の依頼を確認するためにIssueページ をご覧ください．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

## 参考文献
* [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
* [TEN VAD](https://github.com/TEN-framework/ten-vad)
* [module-echo-cancel](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Modules/?utm_source=chatgpt.com#module-echo-cancel)

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>


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