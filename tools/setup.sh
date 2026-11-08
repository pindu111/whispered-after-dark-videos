#!/usr/bin/env bash
# Prepare a fresh workspace: Python deps + the Kokoro voice model (from GitHub releases).
set -e
pip install --break-system-packages -q kokoro-onnx soundfile numpy pillow
mkdir -p "${KOKORO_DIR:=$HOME/kokoro}"
cd "$KOKORO_DIR"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "$f" ] || curl -sSL -o "$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
ls -la "$KOKORO_DIR"
