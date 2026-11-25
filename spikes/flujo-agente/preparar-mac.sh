#!/bin/bash
# Prepara un Mac con Apple Silicon para el MVP con Gemma 4 12B (opción C del README):
# compila llama-server y whisper-server con Metal, descarga y verifica los modelos y crea
# el entorno de Python. Se puede repetir: salta lo que ya está hecho.
# Uso: ./preparar-mac.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
H=${HABLA_HOME:-$HOME/modelos-habla}; M=$H/modelos; S=$H/src

# Mismos commits que la medición del banco (spikes/latencia-voz/README.md).
LLAMA_COMMIT=e4b620af19f02960dea7a3a81de7c5805aa3a333
WHISPER_COMMIT=6680804f99c3982b7d59f27ae315ce880570017e

GEMMA=https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/resolve/main
WHISPER=https://huggingface.co/ggerganov/whisper.cpp/resolve/main
PIPER=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US

fail() { echo "ERROR: $*" >&2; exit 1; }

echo "== 1. Comprobar el equipo"
[ "$(uname -s)" = Darwin ] || fail "este script es para macOS"
[ "$(uname -m)" = arm64 ] || fail "hace falta Apple Silicon (arm64); este equipo es $(uname -m)"
macos=$(sw_vers -productVersion)
[ "${macos%%.*}" -ge 14 ] || fail "hace falta macOS 14 o superior (onnxruntime 1.32 para Piper); este es $macos"
xcode-select -p >/dev/null 2>&1 || fail "faltan las Command Line Tools: xcode-select --install"
for c in git cmake curl uv shasum; do
  command -v $c >/dev/null || fail "falta '$c'. Con Homebrew: brew install cmake uv"
done
ram_gb=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
echo "$(sysctl -n machdep.cpu.brand_string), ${ram_gb} GB, macOS $macos"
[ "$ram_gb" -ge 16 ] || echo "AVISO: con menos de 16 GB el modelo de 12B no cabe; usa un modelo menor"

echo "== 2. Compilar los servidores con Metal"
mkdir -p "$S" "$M"
build() {  # $1 repo, $2 commit, $3 target
  local dir=$S/$(basename "$1" .git)
  if [ -x "$dir/build/bin/$3" ]; then echo "$3 ya compilado"; return; fi
  [ -d "$dir" ] || git clone "$1" "$dir"
  git -C "$dir" fetch --quiet origin "$2" 2>/dev/null || true
  git -C "$dir" checkout --quiet "$2"
  # En Apple Silicon, Metal viene activado por defecto.
  cmake -S "$dir" -B "$dir/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$dir/build" -j --target "$3"
}
build https://github.com/ggml-org/llama.cpp "$LLAMA_COMMIT" llama-server
build https://github.com/ggml-org/whisper.cpp "$WHISPER_COMMIT" whisper-server

echo "== 3. Descargar los modelos (≈ 8,5 GB)"
get() {  # $1 URL; reanuda descargas a medias
  local name; name=$(basename "$1")
  if [ -f "$M/$name" ] && (cd "$M" && grep " $name\$" "$HERE/SHA256SUMS-mac" | shasum -a 256 -c --status); then
    echo "$name ya descargado"; return
  fi
  curl -fL -C - -o "$M/$name" "$1"
}
get $GEMMA/gemma-4-12b-it-Q4_K_M.gguf
get $GEMMA/mtp-gemma-4-12b-it.gguf
get $WHISPER/ggml-small.en.bin
get $PIPER/lessac/medium/en_US-lessac-medium.onnx
get $PIPER/lessac/medium/en_US-lessac-medium.onnx.json
get $PIPER/ryan/medium/en_US-ryan-medium.onnx        # voz del estudiante en bench.py
get $PIPER/ryan/medium/en_US-ryan-medium.onnx.json
(cd "$M" && shasum -a 256 -c "$HERE/SHA256SUMS-mac") || fail "alguna suma no coincide; borra ese archivo y repite"

echo "== 4. Entorno de Python"
[ -x "$H/venv/bin/python" ] || uv venv -p 3.11 "$H/venv"
uv pip install -p "$H/venv/bin/python" \
  -r "$REPO/spikes/latencia-voz/requirements.txt" -r "$HERE/requirements.txt"

echo "== 5. Límite de memoria de la GPU"
limit=$(sysctl -n iogpu.wired_limit_mb 2>/dev/null || echo 0)
if [ "$limit" = 0 ]; then
  echo "macOS usa su límite por defecto (≈ 2/3 de la RAM para la GPU)."
  echo "Si llama-server no carga el modelo, súbelo hasta el próximo reinicio con:"
  echo "  sudo sysctl iogpu.wired_limit_mb=12288"
else
  echo "iogpu.wired_limit_mb = $limit"
fi
echo
echo "Listo. Siguiente paso: ./servidores-mac.sh"
