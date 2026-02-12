#!/bin/bash
set -e

echo "--- Sherpa-ONNX setup (Robust path detection) ---"

sudo apt update
sudo apt install -y pulseaudio-utils ffmpeg

pip3 install -U typing_extensions psutil --break-system-packages
pip3 install "numpy<2.0.0" --force-reinstall --break-system-packages
pip3 install -U git+https://github.com/TEN-framework/ten-vad.git --break-system-packages

HAS_GPU=false
if command -v nvidia-smi &>/dev/null && nvidia-smi -L &>/dev/null; then
  HAS_GPU=true
fi

pip3 uninstall -y sherpa-onnx onnxruntime onnxruntime-gpu --break-system-packages || true

if $HAS_GPU; then
  echo "[GPU detected] Trying GPU wheels..."
  pip3 install onnxruntime-gpu --break-system-packages || true
  pip3 install sherpa-onnx --break-system-packages || true
fi

CUDA_OK=$(python3 - <<'EOF'
import sys
if sys.path[0] == '': sys.path.pop(0)
try:
    import onnxruntime as ort
    print("CUDAExecutionProvider" in ort.get_available_providers())
except:
    print("False")
EOF
)

if $HAS_GPU && [ "$CUDA_OK" = "True" ]; then
  echo "[OK] GPU mode enabled"
else
  echo "[Fallback] Using CPU mode"
  pip3 uninstall -y onnxruntime-gpu --break-system-packages || true
  pip3 install onnxruntime sherpa-onnx --break-system-packages
fi

mkdir -p ~/.sherpa_onnx_asr_models

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
    echo "[Error] Could not detect onnxruntime/capi directory."
fi

# default model download
echo "Downloading default model..."
URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06.tar.bz2"

BASE_DIR="$HOME/.sherpa_onnx_asr_models"
MODEL_DIR="$BASE_DIR/sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06"
TMP_DIR="$BASE_DIR/tmp"
FILE="model.tar.bz2"

mkdir -p "$TMP_DIR"
mkdir -p "$MODEL_DIR"

cd "$TMP_DIR"

if command -v curl >/dev/null 2>&1; then
    curl -L -o "$FILE" "$URL"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$FILE" "$URL"
else
    echo "Please install curl or wget"
    exit 1
fi

tar -xvf "$FILE" -C "$MODEL_DIR" --strip-components=1

rm -f "$FILE"
rmdir "$TMP_DIR" 2>/dev/null || true

echo "----------------------------"
echo "Providers:"
python3 -c "import sys; sys.path.pop(0) if sys.path[0]=='' else None; import onnxruntime as ort; print(ort.get_available_providers())"
echo "Library Path: $LD_LIBRARY_PATH"
echo "--- Done ---"
echo "Please run 'source ~/.bashrc' or restart your terminal."
