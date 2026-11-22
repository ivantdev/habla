#!/usr/bin/env bash
set -euo pipefail

REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
TASK_DIR="$REPO/data/full-duplex"
CODE_REVISION=7fe6b7665f8bf035998f401f8cb779fbe53f2751
export UV_CACHE_DIR="$TASK_DIR/uv-cache"
export UV_HTTP_TIMEOUT=300
export UV_PYTHON_INSTALL_DIR="$TASK_DIR/python"
export XDG_CACHE_HOME="$TASK_DIR/cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
mkdir -p "$TASK_DIR"

if [[ ! -d "$TASK_DIR/Haru" ]]; then
  git clone --no-checkout --depth 1 https://github.com/higurashi-ai/Haru.git "$TASK_DIR/Haru"
  git -C "$TASK_DIR/Haru" fetch --depth 1 origin "$CODE_REVISION"
  git -C "$TASK_DIR/Haru" checkout --detach "$CODE_REVISION"
fi
if [[ "$(git -C "$TASK_DIR/Haru" rev-parse HEAD)" != "$CODE_REVISION" ]]; then
  echo "La revisión local de Haru difiere de la fijada; conserva ese checkout y revisa la configuración." >&2
  exit 1
fi

if [[ ! -x "$TASK_DIR/venv/bin/python" ]]; then
  uv venv --python 3.12 "$TASK_DIR/venv"
fi
uv pip install --python "$TASK_DIR/venv/bin/python" --torch-backend=cu130 \
  -r "$REPO/spikes/full-duplex/requirements.txt"
uv pip install --python "$TASK_DIR/venv/bin/python" --no-deps -e "$TASK_DIR/Haru/haru"

"$TASK_DIR/venv/bin/python" - "$TASK_DIR/model" <<'PY'
import sys
from huggingface_hub import snapshot_download

snapshot_download(
    "higurashi-ai/Haru-4B",
    revision="8d6e83bcd3701a76fc27a764965665da1df7da78",
    local_dir=sys.argv[1],
    allow_patterns=["config.json", "model.safetensors", "tokenizer.json", "README.md"],
)
PY

"$TASK_DIR/venv/bin/python" "$REPO/spikes/full-duplex/prepare_voice.py"
