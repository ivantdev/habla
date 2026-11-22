#!/usr/bin/env bash
set -euo pipefail
REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
TASK_DIR="$REPO/data/full-duplex"
REV=ace091b1841adb2b0588cd609ac06e3dfc261643
export UV_CACHE_DIR="$TASK_DIR/uv-cache"
export UV_HTTP_TIMEOUT=300
export UV_PYTHON_INSTALL_DIR="$TASK_DIR/python"
export XDG_CACHE_HOME="$TASK_DIR/sophon-cache"
mkdir -p "$TASK_DIR"
if [[ ! -d "$TASK_DIR/Sophon" ]]; then
  git clone --no-checkout https://github.com/adventists-ai/sophon-realtime.git "$TASK_DIR/Sophon"
  git -C "$TASK_DIR/Sophon" checkout --detach "$REV"
fi
[[ $(git -C "$TASK_DIR/Sophon" rev-parse HEAD) == "$REV" ]] || {
  echo "La revisión de Sophon difiere de la fijada; conserva y revisa ese checkout." >&2; exit 1;
}
if [[ ! -x "$TASK_DIR/venv-sophon/bin/python" ]]; then
  uv venv --python 3.12 "$TASK_DIR/venv-sophon"
fi
uv pip install --python "$TASK_DIR/venv-sophon/bin/python" \
  -r "$REPO/spikes/full-duplex/requirements-sophon.txt"
uv pip install --python "$TASK_DIR/venv-sophon/bin/python" --no-deps \
  -e "$TASK_DIR/Sophon/flash/plugin"
"$TASK_DIR/venv-sophon/bin/python" - "$TASK_DIR/sophon-model" <<'PY'
import shutil, sys
from huggingface_hub import snapshot_download
from pathlib import Path
target = Path(sys.argv[1])
present = sum(p.stat().st_size for p in target.rglob('*') if p.is_file()) if target.exists() else 0
if shutil.disk_usage(target.parent).free + present < 12_999_734_822 + 3 * 1024**3:
    raise SystemExit('Falta espacio para los pesos y 3 GiB de margen.')
snapshot_download('adventists-ai/Sophon-Realtime-4B-Flash',
    revision='8597f03bcc95d02115b0657823784e8aab5bb737', local_dir=target, max_workers=2)
PY
uv pip check --python "$TASK_DIR/venv-sophon/bin/python"
