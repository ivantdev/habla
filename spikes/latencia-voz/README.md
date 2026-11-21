# Banco de latencia de la ruta de voz

Prototipo desechable para [S05-P-02](../../docs/specs/SPEC-05-voice-conversation.md): mide la latencia de cada modelo de la ruta ASR → LLM → TTS en una conversación simulada turno a turno. No es código de producto. Análisis completo y resultados: [LATENCIA-Y-CONTEXTO-VOZ.md](../../docs/experiments/LATENCIA-Y-CONTEXTO-VOZ.md), sección 7.

## Qué se hizo

`bench.py` simula una conversación con el tutor que crece turno a turno, con los modelos reales cargados en la GPU:

1. Sintetiza con Piper (voz `ryan`) 10 frases de un estudiante B1 sobre el tema restaurante, a 16 kHz, de 1,7 a 5,2 s. Se usan en ciclo.
2. En cada turno envía el audio a `whisper-server` (ASR final, `t2 − t1`).
3. Agrega la transcripción al historial y lo envía a `llama-server` en streaming. Mide el primer token (`t3 − t2`) y la primera frase completa (`t4 − t3`).
4. Sintetiza esa primera frase con Piper y con Kokoro en CPU (primer audio, `t5 − t4`).
5. Agrega la respuesta completa del tutor al historial y pasa al turno siguiente.

El prompt de sistema se arma desde [POLITICA-TUTOR.md](../../docs/content/POLITICA-TUTOR.md) y [FICHAS.md](../../docs/content/FICHAS.md) (B1, restaurante, fase `conversation`; 773 tokens). La espera de silencio (`t1 − t0`, 600 ms) es un parámetro (`--hangover-ms`), y el canal (`t7 − t5`, 85 ms) sale del [spike de audio](../audio-channel/README.md) (`--channel-ms`). Ambos se suman a lo medido para estimar `t7 − t0`.

Cada corrida ejecuta dos sesiones: con caché de prefijo del LLM (`cache_prompt: true`) y sin ella. En la sesión sin caché, `cache_n` vale 0 en todos los turnos, así que se procesa el contexto completo cada vez.

## Resultados resumidos

Corrida de 100 turnos del 2026-11-18 en una RTX 5060 Ti de 16 GB. El contexto crece de 791 a ≈ 4900 tokens. Valores en ms, p50 / p95 / máx.

| Tramo | Con caché | Sin caché |
| --- | --- | --- |
| ASR final | 99 / 117 / 121 | 99 / 117 / 120 |
| Primer token | 33 / 39 / 41 | 805 / 1369 / 1432 |
| Primera frase | 61 / 107 / 112 | 74 / 133 / 140 |
| TTS Piper, CPU | 35 / 70 / 146 | 43 / 74 / 78 |
| TTS Kokoro, CPU | 355 / 442 / 493 | 372 / 464 / 501 |
| **Total `t7 − t0`, Piper** | **922 / 973 / 1072** | 1683 / 2276 / 2387 |
| Total `t7 − t0`, Kokoro | 1250 / 1338 / 1392 | 2015 / 2665 / 2806 |

- Con caché, los modelos suman ≈ 240 ms en p50. El resto del total son la espera de silencio (600 ms) y el canal (85 ms), que se suponen y no se miden.
- Con caché, el primer token no crece con la duración de la charla. Sin caché, el p95 total supera los 2 s de referencia de RNF-01.
- Memoria de la GPU 0: 7956 MiB de 16 311 con Whisper y Qwen3 (contexto de 8192).

**Por qué las cifras son optimistas** (detalle en §7.3 y §7.5 del análisis):

- En 100 turnos solo hay 10 primeras frases distintas: el tutor repite su respuesta cuando el audio del estudiante se repite.
- Las primeras frases son cortas: 4,5 palabras de mediana.
- Las etapas se miden en secuencia. No hay ASR incremental, ni LLM decodificando mientras el TTS sintetiza, ni evaluador cargado.
- El audio del estudiante es sintético y dura como mucho 5,2 s.

## Replicación

### Entorno de la medición original

| Elemento | Versión |
| --- | --- |
| Equipo | 2× RTX 5060 Ti de 16 GB (solo se usa la GPU 0), 24 hilos de CPU, 26 GB de RAM |
| Sistema | Linux, controlador NVIDIA 595.99.02, CUDA 13.1 (`nvcc` V13.1.115) |
| llama.cpp | `e4b620af19f02960dea7a3a81de7c5805aa3a333` |
| whisper.cpp | `6680804f99c3982b7d59f27ae315ce880570017e` |
| Python | 3.11.17, paquetes en [requirements.txt](requirements.txt) |
| Modelos | Sumas SHA-256 en [SHA256SUMS](SHA256SUMS) |

Los modelos y los binarios quedan fuera del repositorio, en `~/modelos-habla/`. Ocupan unos 7 GB de modelos más las compilaciones.

### 1. Compilar los servidores

Los commits fijados son los de la medición. Para otra GPU, ajusta `CMAKE_CUDA_ARCHITECTURES` (120 = RTX serie 50, 89 = RTX 4090).

```bash
mkdir -p ~/modelos-habla/src ~/modelos-habla/modelos
cd ~/modelos-habla/src
git clone https://github.com/ggml-org/llama.cpp
git -C llama.cpp checkout e4b620af19f02960dea7a3a81de7c5805aa3a333
git clone https://github.com/ggml-org/whisper.cpp
git -C whisper.cpp checkout 6680804f99c3982b7d59f27ae315ce880570017e

cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120 -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build -j --target llama-server
cmake -S whisper.cpp -B whisper.cpp/build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120 -DCMAKE_BUILD_TYPE=Release
cmake --build whisper.cpp/build -j --target whisper-server
```

### 2. Descargar los modelos y el entorno de Python

```bash
cd ~/modelos-habla/modelos
curl -LO https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf
curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

cd ~/modelos-habla
uv venv -p 3.11 venv
uv pip install -p venv/bin/python -r "<repo>/spikes/latencia-voz/requirements.txt"
venv/bin/python -m piper.download_voices en_US-lessac-medium en_US-ryan-medium --download-dir modelos

# Debe validar los 8 archivos sin errores
cd modelos && sha256sum -c "<repo>/spikes/latencia-voz/SHA256SUMS"
```

Si una suma no coincide, el archivo publicado cambió. Anota la suma nueva junto a los resultados, porque la medición ya no es la misma.

### 3. Arrancar los servidores

En dos terminales, ambos en la GPU 0 (la ruta completa en una GPU, sección 4 del análisis):

```bash
M=~/modelos-habla/modelos; S=~/modelos-habla/src
CUDA_VISIBLE_DEVICES=0 $S/llama.cpp/build/bin/llama-server -m $M/Qwen3-8B-Q4_K_M.gguf \
  -ngl 99 -c 8192 -np 1 --jinja --port 8081
```

```bash
M=~/modelos-habla/modelos; S=~/modelos-habla/src
CUDA_VISIBLE_DEVICES=0 $S/whisper.cpp/build/bin/whisper-server -m $M/ggml-large-v3-turbo.bin \
  --port 8082 -l en
```

Ambos escuchan solo en `127.0.0.1`. Espera a que terminen de cargar los modelos antes de lanzar el banco.

### 4. Ejecutar las corridas

Desde `spikes/latencia-voz/`:

```bash
# Primera medición (30 turnos por modo)
~/modelos-habla/venv/bin/python bench.py --turns 30 --label "5060ti-qwen3-8b-q4km-whisper-turbo"

# Corrida de 100 turnos por modo, el mínimo de METRICS §7
~/modelos-habla/venv/bin/python bench.py --turns 100 --label "5060ti-qwen3-8b-q4km-whisper-turbo-100"
```

Cada corrida imprime una tabla p50/p95/máx por tramo y guarda el detalle por turno en `out/bench-<fecha>.json`, que no se versiona (`spikes/**/out/` está en `.gitignore`). El JSON incluye para cada turno:

- el texto transcrito y la primera frase del tutor;
- `prompt_tokens`, `cache_n` y `prompt_n` (tokens totales, reutilizados de la caché y procesados);
- la velocidad de decodificación.

Otros parámetros: `--hangover-ms`, `--channel-ms`, `--max-tokens` (120) y `--modes` (`cache,nocache`).

### Qué esperar al replicar

- El LLM usa temperatura 0,7 sin semilla fija: las respuestas y los milisegundos varían entre corridas. Con la misma GPU, los p50 deberían quedar a unos pocos ms de la tabla.
- En otra GPU cambian los tramos de ASR, prefill y decodificación. Los TTS en CPU dependen del procesador.
- Para comprobar que la caché funciona, mira `cache_n` en el JSON: con caché debe crecer turno a turno, y sin caché debe ser 0.
