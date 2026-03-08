#!/bin/bash
set -e

echo "--- Sherpa-ONNX setup (Standard CPU version) ---"

sudo apt update
sudo apt install -y pulseaudio-utils ffmpeg curl wget bzip2

pip3 install -U typing_extensions psutil --break-system-packages
pip3 install "numpy==1.26.4" --force-reinstall --break-system-packages
pip3 install -U git+https://github.com/TEN-framework/ten-vad.git --break-system-packages

echo "Installing onnxruntime (CPU) and sherpa-onnx..."
pip3 uninstall -y sherpa-onnx onnxruntime onnxruntime-gpu --break-system-packages || true
pip3 install onnxruntime sherpa-onnx --break-system-packages

BASE_DIR="$HOME/.sherpa_onnx_asr_models"
mkdir -p "$BASE_DIR"

echo "Configuring LD_LIBRARY_PATH..."

ORT_LIB_PATH=$(python3 - <<'EOF'
import sys
import os
if sys.path[0] == '': sys.path.pop(0)
try:
    import onnxruntime
    print(os.path.dirname(onnxruntime.__file__) + '/capi')
except:
    pass
EOF
)

if [ -n "$ORT_LIB_PATH" ] && [ -d "$ORT_LIB_PATH" ]; then
    if ! grep -q "$ORT_LIB_PATH" ~/.bashrc; then
        echo "Adding $ORT_LIB_PATH to ~/.bashrc"
        echo "export LD_LIBRARY_PATH=\"$ORT_LIB_PATH:\$LD_LIBRARY_PATH\"" >> ~/.bashrc
        export LD_LIBRARY_PATH="$ORT_LIB_PATH:$LD_LIBRARY_PATH"
        echo "[Success] Path added to .bashrc"
    else
        echo "[Info] LD_LIBRARY_PATH is already configured in .bashrc"
    fi
else
    echo "[Warning] Could not detect onnxruntime/capi directory. Internal library resolution might fail."
fi

echo "Downloading default model..."
MODEL_NAME="sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06"
URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/${MODEL_NAME}.tar.bz2"
MODEL_DIR="$BASE_DIR/$MODEL_NAME"

if [ ! -d "$MODEL_DIR" ]; then
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    echo "Downloading to $TMP_DIR..."
    wget -O model.tar.bz2 "$URL"
    
    mkdir -p "$MODEL_DIR"
    tar -xvf model.tar.bz2 -C "$MODEL_DIR" --strip-components=1
    
    cd ~
    rm -rf "$TMP_DIR"
    echo "[Success] Model installed to $MODEL_DIR"
else
    echo "[Info] Model already exists. Skipping download."
fi

echo "----------------------------"
echo "Installation Summary:"
python3 -c "import sys; sys.path.pop(0) if sys.path[0]=='' else None; import onnxruntime as ort; print('Available Providers:', ort.get_available_providers())"
echo "Model Directory: $BASE_DIR"
echo "--- Done ---"
echo "Please run 'source ~/.bashrc' to apply changes."