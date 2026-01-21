#!/bin/bash
set -e

echo "--- Sherpa-ONNX setup (Robust path detection) ---"

sudo apt update
sudo apt install -y pulseaudio-utils ffmpeg

pip3 install -U typing_extensions psutil
pip3 install "numpy<2.0.0" --force-reinstall
pip3 install -U git+https://github.com/TEN-framework/ten-vad.git

HAS_GPU=false
if command -v nvidia-smi &>/dev/null && nvidia-smi -L &>/dev/null; then
  HAS_GPU=true
fi

pip uninstall -y sherpa-onnx onnxruntime onnxruntime-gpu || true

if $HAS_GPU; then
  echo "[GPU detected] Trying GPU wheels..."
  pip install onnxruntime-gpu || true
  pip install sherpa-onnx || true
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
  pip uninstall -y onnxruntime-gpu || true
  pip install onnxruntime sherpa-onnx
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

echo "----------------------------"
echo "Providers:"
python3 -c "import sys; sys.path.pop(0) if sys.path[0]=='' else None; import onnxruntime as ort; print(ort.get_available_providers())"
echo "Library Path: $LD_LIBRARY_PATH"
echo "--- Done ---"
echo "Please run 'source ~/.bashrc' or restart your terminal."