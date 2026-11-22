#!/bin/bash
# Arranca whisper-server (GPU 1) y llama-server con Gemma 4 31B en las dos GPU,
# con la configuración de la §9.5 de docs/experiments/CALIDAD-Y-LATENCIA-TUTOR.md.
# Uso: ./servidores-gemma.sh        Para apagarlos: ./servidores-gemma.sh stop
set -euo pipefail
H=${HABLA_HOME:-~/modelos-habla}; M=$H/modelos; S=$H/src

stop() {
  for p in $H/llama-server.pid $H/whisper-server.pid; do
    if [ -f "$p" ] && kill -0 "$(cat "$p")" 2>/dev/null; then kill "$(cat "$p")"; fi
    rm -f "$p"
  done
}
wait_up() {  # $1 URL, $2 archivo PID, $3 nombre, $4 log
  for _ in $(seq 1 180); do
    curl -sf "$1" >/dev/null && { echo "$3 listo"; return; }
    kill -0 "$(cat "$2")" 2>/dev/null || { echo "$3 no arrancó; revisa $4"; tail -5 "$4"; exit 1; }
    sleep 1
  done
  echo "$3 no respondió en 3 minutos; revisa $4"; exit 1
}

if [ "${1:-}" = stop ]; then stop; echo "servidores apagados"; exit 0; fi
stop

CUDA_VISIBLE_DEVICES=1 nohup $S/whisper.cpp/build/bin/whisper-server -m $M/ggml-large-v3-turbo.bin \
  --port 8082 -l en > $H/whisper-server.log 2>&1 &
echo $! > $H/whisper-server.pid
wait_up http://127.0.0.1:8082/ $H/whisper-server.pid whisper-server $H/whisper-server.log

nohup $S/llama.cpp/build/bin/llama-server -m $M/gemma-4-31B-it-Q4_K_M.gguf \
  -ngl 99 -c 8192 -np 1 --jinja --port 8081 \
  -sm tensor -fa on --swa-full \
  --spec-type draft-mtp -md $M/mtp-gemma-4-31B-it.gguf --spec-draft-n-max 3 \
  > $H/llama-server.log 2>&1 &
echo $! > $H/llama-server.pid
wait_up http://127.0.0.1:8081/health $H/llama-server.pid llama-server $H/llama-server.log

nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
