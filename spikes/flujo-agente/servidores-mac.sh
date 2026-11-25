#!/bin/bash
# Arranca whisper-server y llama-server con Gemma 4 12B en un Mac con Apple Silicon
# (opción C del README). Requiere haber ejecutado ./preparar-mac.sh.
# Uso: ./servidores-mac.sh        Para apagarlos: ./servidores-mac.sh stop
# Variables opcionales:
#   CTX=4096                   contexto del LLM; 8192 es el de las mediciones, pero ocupa más memoria
#   MTP=1                      decodificación especulativa con el cabezal MTP; MTP=0 la desactiva
#   KV=f16                     tipo de la caché; KV=q8_0 ahorra memoria, pero cambia la configuración medida
#   WHISPER=ggml-small.en.bin  modelo de Whisper dentro de $HABLA_HOME/modelos
set -euo pipefail
H=${HABLA_HOME:-$HOME/modelos-habla}; M=$H/modelos; S=$H/src
CTX=${CTX:-4096}; MTP=${MTP:-1}; KV=${KV:-f16}; WHISPER=${WHISPER:-ggml-small.en.bin}

stop() {
  for p in "$H/llama-server.pid" "$H/whisper-server.pid"; do
    if [ -f "$p" ] && kill -0 "$(cat "$p")" 2>/dev/null; then kill "$(cat "$p")"; fi
    rm -f "$p"
  done
}
wait_up() {  # $1 URL, $2 archivo PID, $3 nombre, $4 log
  for _ in $(seq 1 300); do
    curl -sf "$1" >/dev/null && { echo "$3 listo"; return; }
    kill -0 "$(cat "$2")" 2>/dev/null || { echo "$3 no arrancó; revisa $4"; tail -5 "$4"; exit 1; }
    sleep 1
  done
  echo "$3 no respondió en 5 minutos; revisa $4"; exit 1
}
rss_mb() { echo $(( $(ps -o rss= -p "$(cat "$1")") / 1024 )); }

if [ "${1:-}" = stop ]; then stop; echo "servidores apagados"; exit 0; fi
stop

if [ "$(sysctl -n iogpu.wired_limit_mb 2>/dev/null || echo 0)" = 0 ]; then
  echo "Aviso: límite de la GPU por defecto. Si llama-server falla al reservar memoria:"
  echo "  sudo sysctl iogpu.wired_limit_mb=12288   (o prueba CTX=2048, KV=q8_0 o MTP=0)"
fi

nohup "$S/whisper.cpp/build/bin/whisper-server" -m "$M/$WHISPER" \
  --port 8082 -l en > "$H/whisper-server.log" 2>&1 &
echo $! > "$H/whisper-server.pid"
wait_up http://127.0.0.1:8082/ "$H/whisper-server.pid" whisper-server "$H/whisper-server.log"

# Igual que la §8 de CALIDAD-Y-LATENCIA-TUTOR.md (-ngl 99 -np 1 --jinja --swa-full), con el contexto
# reducido y, como en la §9 del 31B, flash attention y el cabezal MTP.
args=(-m "$M/gemma-4-12b-it-Q4_K_M.gguf" -ngl 99 -c "$CTX" -np 1 --jinja --port 8081 -fa on --swa-full)
if [ "$MTP" = 1 ]; then
  args+=(--spec-type draft-mtp -md "$M/mtp-gemma-4-12b-it.gguf" --spec-draft-n-max 3)
fi
if [ "$KV" != f16 ]; then args+=(-ctk "$KV" -ctv "$KV"); fi

nohup "$S/llama.cpp/build/bin/llama-server" "${args[@]}" > "$H/llama-server.log" 2>&1 &
echo $! > "$H/llama-server.pid"
wait_up http://127.0.0.1:8081/health "$H/llama-server.pid" llama-server "$H/llama-server.log"

echo "Configuración: CTX=$CTX MTP=$MTP KV=$KV WHISPER=$WHISPER"
echo "Memoria residente (orientativa): llama-server $(rss_mb "$H/llama-server.pid") MB," \
  "whisper-server $(rss_mb "$H/whisper-server.pid") MB"
grep -m1 -i "recommendedMaxWorkingSetSize" "$H/llama-server.log" || true
