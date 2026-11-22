#!/usr/bin/env bash
set -euo pipefail

REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
export XDG_CACHE_HOME="$REPO/data/full-duplex/cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TRITON_CACHE_DIR="$XDG_CACHE_HOME/triton"
export HF_HUB_OFFLINE=1
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="${HARU_GPU:-0}"
mkdir -p "$REPO/spikes/full-duplex/out"
exec > >(tee -a "$REPO/spikes/full-duplex/out/server.log") 2>&1

exec "$REPO/data/full-duplex/venv/bin/python" "$REPO/spikes/full-duplex/diagnostic_server.py" \
  --model "$REPO/data/full-duplex/model" \
  --device cuda --host 127.0.0.1 --port 8998 \
  --max-sessions 1 --time-limit 900 --network-profile local --webrtc off \
  --seed 20261120 --language es --codec-backend torch "$@"
