import os
import glob

def is_landmine_model(directory):
    name = os.path.basename(directory).lower()

    blocked_keywords = [
        "cann", "android", "ios",
        "aarch64", "arm64", "arm", 
        "qnn", "rknn", "horizon", "coreml",
        "ncnn", "libtorch",
        "rk35", "rk33", "rockchip"
    ]
    for k in blocked_keywords:
        if k in name:
            return True, f"blocked keyword: {k}"

    if not os.path.exists(directory):
        return True, "directory does not exist"

    try:
        files = os.listdir(directory)
    except OSError:
        return True, "could not list directory"
    
    for f in files:
        f_low = f.lower()
        if f_low.endswith((".pt", ".pth", ".tflite", ".bin", ".param")):
            if "ncnn" in f_low or "openvino" in name:
                return True, f"unsupported format: {f}"

    if not any(f.endswith(".onnx") for f in files):
        return True, "no onnx model found"

    if "tokens.txt" not in files and "bpe.model" not in files:
        return True, "tokens.txt or bpe.model missing"

    return False, None

def find_file(directory, *keywords):
    try:
        candidates = [
            f for f in os.listdir(directory)
            if f.endswith(".onnx") and all(k in f.lower() for k in keywords)
        ]

        if candidates:
            int8 = [f for f in candidates if "int8" in f.lower()]
            best = int8[0] if int8 else candidates[0]
            return os.path.join(directory, best)

        pattern = os.path.join(directory, "**", "*.onnx")
        for path in glob.glob(pattern, recursive=True):
            name = os.path.basename(path).lower()
            if all(k in name for k in keywords):
                return path
        return None
        
    except Exception:
        return None

def find_recursive(directory, filename):
    for root, dirs, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None

def find_tokens(directory):
    path = os.path.join(directory, "tokens.txt")
    if os.path.exists(path): return path
    try:
        for f in os.listdir(directory):
            if f.endswith("tokens.txt"): return os.path.join(directory, f)
    except OSError: pass
    return None

def inspect_offline_model_type(directory):
    dir_name = os.path.basename(directory).lower()
    
    if "canary" in dir_name: return "nemo_canary"
    if "sense" in dir_name: return "sense_voice"
    if "moonshine" in dir_name: return "moonshine"
    if "fire" in dir_name and "red" in dir_name: return "fire_red_asr"
    if "paraformer" in dir_name: return "paraformer"
    if "dolphin" in dir_name: return "dolphin"
    if "med" in dir_name and "asr" in dir_name: return "medasr"
    if "tele" in dir_name: return "telespeech"
    if "zipformer" in dir_name: return "zipformer"
    if "omnilingual" in dir_name: return "omnilingual"
    if "yesno" in dir_name or "tdnn" in dir_name: return "tdnn"
    if "wenet" in dir_name: return "wenet"
    if "whisper" in dir_name: return "whisper"

    def _has(k): return find_file(directory, k) is not None

    if _has("llm"): return "fun_asr_nano"
    if find_file(directory, "preprocess"): return "moonshine"
    if _has("joiner"): return "transducer"
    if _has("decoder"): return "whisper"
    
    return "nemo_ctc"

def inspect_online_model_type(directory):
    dir_name = os.path.basename(directory).lower()
    
    has_joiner = find_file(directory, "joiner") is not None
    has_decoder = find_file(directory, "decoder") is not None
    has_encoder = find_file(directory, "encoder") is not None
    
    if has_joiner and has_decoder and has_encoder:
        return "transducer"

    if has_encoder and has_decoder and not has_joiner:
        return "paraformer"

    if "t_one" in dir_name or "tone" in dir_name: return "t_one_ctc"
    
    if "wenet" in dir_name and not has_joiner: return "wenet_ctc"
    
    if "nemo" in dir_name: return "nemo_ctc"
    
    if "zipformer" in dir_name: return "zipformer2_ctc"

    return "transducer"