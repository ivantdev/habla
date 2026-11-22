#!/usr/bin/env bash
set -euo pipefail
REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
TASK_DIR="$REPO/data/full-duplex"
SPIKE="$REPO/spikes/full-duplex"
export PATH="$TASK_DIR/venv-sophon/bin:$PATH"
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=${SOPHON_GPU:-0}
export XDG_CACHE_HOME="$TASK_DIR/sophon-cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export HF_HUB_OFFLINE=1
export FLASHINFER_WORKSPACE_BASE="$XDG_CACHE_HOME/flashinfer"
export SOPHON_MODEL="$TASK_DIR/sophon-model"
export SOPHON_PORT=8000
export SOPHON_SELF_URL=http://127.0.0.1:8000
export VLLM_DISABLE_COMPILE_CACHE=1
mkdir -p "$SPIKE/out" "$XDG_CACHE_HOME"

# Mismo esquema de concurrencia del arranque oficial, con directorios propios.
MPS_STARTED=0
if [[ ${SOPHON_MPS:-1} == 1 ]] && command -v nvidia-cuda-mps-control >/dev/null; then
  export CUDA_MPS_PIPE_DIRECTORY="$TASK_DIR/sophon-mps/gpu${SOPHON_GPU:-0}/pipe"
  export CUDA_MPS_LOG_DIRECTORY="$TASK_DIR/sophon-mps/gpu${SOPHON_GPU:-0}/log"
  mkdir -p "$CUDA_MPS_PIPE_DIRECTORY" "$CUDA_MPS_LOG_DIRECTORY"
  if ! echo get_server_list | nvidia-cuda-mps-control >/dev/null 2>&1; then
    nvidia-cuda-mps-control -d
    MPS_STARTED=1
  fi
  export CUDA_VISIBLE_DEVICES=0
fi
cleanup() {
  kill "$UI_PID" 2>/dev/null || true
  if [[ $MPS_STARTED == 1 ]]; then echo quit | nvidia-cuda-mps-control >/dev/null 2>&1 || true; fi
}
python -m http.server 8999 --bind 127.0.0.1 --directory "$SPIKE/sophon-web" \
  > "$SPIKE/out/sophon-web.log" 2>&1 &
UI_PID=$!
trap cleanup EXIT
python - "$TASK_DIR/Sophon/flash" "$SPIKE/out/sophon-deploy.yaml" <<'PY'
import sys, yaml
from pathlib import Path
root, target = map(Path, sys.argv[1:])
config = yaml.safe_load((root/'config/sophon_realtime_flash_4b.yaml').read_text().replace('__HERE__', str(root)))
config['duplex_session']['max_sessions'] = 1
target.write_text(yaml.safe_dump(config, sort_keys=False))
PY
echo 'Sophon: interfaz http://127.0.0.1:8999; espera /health en el puerto 8000.'
python "$SPIKE/serve_sophon.py" serve "$SOPHON_MODEL" --omni --host 127.0.0.1 --port 8000 \
  --trust-remote-code --init-timeout 3000 --stage-init-timeout 3000 \
  --deploy-config "$SPIKE/out/sophon-deploy.yaml" "$@" \
  2>&1 | tee -a "$SPIKE/out/sophon-server.log"
