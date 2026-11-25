# MVP del flujo del agente de voz

Prototipo desechable para probar a mano el recorrido de [SPEC-05](../../docs/specs/SPEC-05-voice-conversation.md) con los modelos reales. No es código de producto: el canal y la orquestación reales se construyen en SPEC-00/04/05.

La página tiene un botón **Empezar/Terminar** y, al lado, la transcripción de la conversación. Bajo cada respuesta del tutor aparecen sus latencias: ASR, primer token y primer audio.

## Flujo

1. Al conectar, el tutor abre la conversación con el prompt de [POLITICA-TUTOR.md](../../docs/content/POLITICA-TUTOR.md) y [FICHAS.md](../../docs/content/FICHAS.md). Por defecto usa el nivel B1 y el tema restaurante, y lo arma con `build_system_prompt` del [banco de latencia](../latencia-voz/README.md).
2. El navegador envía el micrófono como PCM s16le de 16 kHz. Usa el mismo worklet del [spike de audio](../audio-channel/README.md), con cancelación de eco activada.
3. El servidor detecta el fin de turno por energía: el turno empieza cuando el RMS supera `--rms` (0,02) y termina tras `--hangover-ms` (600 ms) de silencio. Los turnos con menos de `--min-speech-ms` (300 ms) de voz se descartan.
4. El turno se transcribe con `whisper-server` y el historial completo va a `llama-server` en streaming, con la caché de prefijo activa.
5. Cada frase completa se sintetiza con Piper en CPU y se envía al navegador en cuanto está lista, sin esperar al resto de la respuesta.
6. Cuando el navegador termina de reproducir, avisa al servidor (`playback_ended`) y este vuelve a escuchar.

## Simplificaciones

- **Semidúplex:** mientras el tutor piensa o habla, el audio del estudiante se descarta. No hay interrupción.
- No hay temporizador, fases, frases ancla, consentimiento ni grabación: el audio no se guarda.
- El protocolo es mínimo: frames binarios sin cabecera y eventos JSON propios. No sigue C-04.
- El umbral de energía es fijo. Con ruido de fondo puede no cerrar el turno; en ese caso, sube `--rms`.

## Uso

Necesita `llama-server` en el puerto 8081 y `whisper-server` en el 8082, compilados como en la [sección 1 de la replicación del banco](../latencia-voz/README.md#1-compilar-los-servidores), y el entorno `~/modelos-habla/venv` de ese banco, al que se añaden FastAPI y Uvicorn:

```bash
uv pip install -p ~/modelos-habla/venv/bin/python -r requirements.txt
```

### Opción A: Gemma 4 31B en dos GPU (recomendada)

Es el modelo y la configuración que salieron mejor en la [§9 de calidad y latencia](../../docs/experiments/CALIDAD-Y-LATENCIA-TUTOR.md#9-configuración-optimizada-de-gemma-4-31b-y-qwen38-27b-2026-11-22). Requiere dos GPU de 16 GB: el modelo ocupa las dos y Whisper va en la GPU 1. Usa ≈ 13,6 GB en la GPU 0 y 15,5 GB en la GPU 1.

1. **Descargar el modelo y su cabezal MTP** (18,3 GB y 0,51 GB):

   ```bash
   cd ~/modelos-habla/modelos
   curl -LO https://huggingface.co/unsloth/gemma-4-31B-it-GGUF/resolve/main/gemma-4-31B-it-Q4_K_M.gguf
   curl -LO https://huggingface.co/unsloth/gemma-4-31B-it-GGUF/resolve/main/mtp-gemma-4-31B-it.gguf
   sha256sum gemma-4-31B-it-Q4_K_M.gguf mtp-gemma-4-31B-it.gguf
   # 38bd64c852c4b460434cc7162fa9bdcf242faf86502581a754cb72956bb17f84  gemma-4-31B-it-Q4_K_M.gguf
   # 5ae8b0117bed601e8924c6305bd5b0585de361d51f0e77091bcb4252cf1f27de  mtp-gemma-4-31B-it.gguf
   ```

2. **Arrancar los servidores** con [`servidores-gemma.sh`](servidores-gemma.sh). Espera a que los dos digan «listo»; la primera carga del modelo desde disco tarda un par de minutos:

   ```bash
   ./servidores-gemma.sh          # ./servidores-gemma.sh stop para apagarlos
   ```

   El script arranca `llama-server` con estas opciones, además de `-ngl 99 -c 8192 -np 1 --jinja`:

   | Opción | Para qué |
   | --- | --- |
   | `-sm tensor -fa on` | Reparte cada capa entre las dos GPU para que trabajen a la vez (experimental; funciona sin NCCL) |
   | `--swa-full` | Caché SWA completa: sin ella cada turno guarda copias de la caché en RAM y añade cientos de ms ([§8.2](../../docs/experiments/CALIDAD-Y-LATENCIA-TUTOR.md#82-diagnóstico-checkpoints-de-la-caché-swa-en-gemma-4)) |
   | `--spec-type draft-mtp -md mtp-gemma-4-31B-it.gguf --spec-draft-n-max 3` | Decodificación especulativa: el cabezal MTP propone 3 tokens y el modelo los verifica de una vez |

   Juntas, llevan la decodificación de 20 a ≈ 61 tokens/s. Whisper tiene que ir en la GPU 1: en la GPU 0 no cabe con esta configuración.

3. **Arrancar la interfaz:**

   ```bash
   ~/modelos-habla/venv/bin/python server.py       # http://127.0.0.1:8000
   ```

### Opción B: Qwen3 8B en una GPU

Es la configuración original del spike y la del [banco de latencia](../latencia-voz/README.md#3-arrancar-los-servidores). Arranca los dos servidores en la GPU 0 como indica ese enlace y después `server.py`. Es rápido, pero **no cumple la política del tutor** en los casos de seguridad: crisis, consulta legal y petición de hablar en español ([§2](../../docs/experiments/CALIDAD-Y-LATENCIA-TUTOR.md#2-calidad)).

### Opción C: Gemma 4 12B en un Mac con Apple Silicon

Sirve para desarrollar y hacer demos sin las GPU. Es el mismo modelo de la [§8 de calidad y latencia](../../docs/experiments/CALIDAD-Y-LATENCIA-TUTOR.md#8-comparación-con-otros-modelos-2026-11-22): resuelve bien los casos de español, legal y sentimental, pero **falla la crisis** (TUT-15, 2 de 9). Sus latencias **no son comparables** con las de las GPU.

Requisitos: Apple Silicon con 16 GB o más, macOS 14 o superior, unos 10 GB libres en disco, las Command Line Tools (`xcode-select --install`) y `brew install cmake uv`.

1. **Preparar el equipo** con [`preparar-mac.sh`](preparar-mac.sh). Compila `llama-server` y `whisper-server` con Metal en los commits del banco, descarga los modelos y los comprueba con [`SHA256SUMS-mac`](SHA256SUMS-mac). Después crea el entorno `~/modelos-habla/venv`. Se puede repetir: salta lo que ya está hecho.

   ```bash
   cd spikes/flujo-agente
   ./preparar-mac.sh
   ```

   | Modelo | Tamaño | Para qué |
   | --- | --- | --- |
   | `gemma-4-12b-it-Q4_K_M.gguf` | 7,1 GB | LLM del tutor, el mismo GGUF de la §8 |
   | `mtp-gemma-4-12b-it.gguf` | 0,47 GB | Cabezal MTP para la decodificación especulativa |
   | `ggml-small.en.bin` | 0,49 GB | Whisper `small.en`, en lugar de `large-v3-turbo`, para ahorrar memoria |
   | Piper `lessac` y `ryan` | 0,13 GB | Voz del tutor y voz del estudiante sintético de `bench.py` |

2. **Arrancar los servidores** con [`servidores-mac.sh`](servidores-mac.sh). La primera carga tarda unos minutos.

   ```bash
   ./servidores-mac.sh          # ./servidores-mac.sh stop para apagarlos
   ```

   Usa la configuración de la §8 (`-ngl 99 -np 1 --jinja --swa-full`), con estos cambios:

   | Cambio | Por qué | Variable |
   | --- | --- | --- |
   | Contexto de 4096 en lugar de 8192 | Con `--swa-full`, la caché crece con el contexto; 4096 alcanza para una sesión corta | `CTX` |
   | `-fa on` y cabezal MTP (`--spec-draft-n-max 3`) | En el Mac, la decodificación es el cuello de botella; en el 31B el MTP subió los tokens/s ≈ 1,7× | `MTP=0` lo desactiva |
   | Whisper `small.en` | Unos 1–1,5 GB menos que `large-v3-turbo`; transcribe algo peor con acento fuerte | `WHISPER` |
   | Caché `q8_0` (opcional) | Ahorra memoria si no cabe; no se ha medido su efecto en la calidad | `KV=q8_0` |

   Por defecto, macOS deja a la GPU unos 2/3 de la RAM (≈ 10,7 GB con 16 GB). Si `llama-server` falla al reservar memoria, en este orden:

   - sube el límite hasta el próximo reinicio con `sudo sysctl iogpu.wired_limit_mb=12288`;
   - o prueba `CTX=2048`, `KV=q8_0` o `MTP=0`.

   Cierra antes las aplicaciones pesadas.

3. **Arrancar la interfaz**, igual que en las otras opciones:

   ```bash
   ~/modelos-habla/venv/bin/python server.py       # http://127.0.0.1:8000
   ```

4. **Medir la latencia en el Mac** con el banco, que reutiliza los mismos servidores. Anota el chip (M1, M1 Pro…) en la etiqueta y lee las pautas de [probar en otro hardware](../latencia-voz/README.md#probar-en-otro-hardware). Desde `spikes/latencia-voz/`:

   ```bash
   ~/modelos-habla/venv/bin/python bench.py --turns 30 --modes cache --label "m1-16gb-gemma4-12b-q4km-mtp-ctx4096-whisper-small"
   ```

**Qué esperar (estimación, sin medir):** en un M1 base (68 GB/s de memoria), la decodificación de un 12B en 4 bits queda en ≈ 7–9 tokens/s sin MTP. La primera frase tardaría ≈ 2–2,5 s y el total desde el fin de la voz, ≈ 4–5 s. En un M1 Pro (200 GB/s), ≈ 2–2,5 s en total. La apertura de la sesión procesa el prompt completo (≈ 770 tokens) y puede tardar varios segundos; los turnos siguientes usan la caché.

### En el navegador

Abre `http://127.0.0.1:8000`, pulsa **Empezar** y permite el micrófono. En `localhost` el micrófono funciona sin HTTPS.

- **Usa audífonos.** La cancelación de eco del navegador ayuda, pero con altavoces el tutor puede oírse a sí mismo al final de cada respuesta.
- **No interrumpas:** mientras el tutor habla, el micrófono se ignora.
- **El turno se cierra tras 0,6 s de silencio.** Si te corta a mitad de frase, sube `--hangover-ms`; si no cierra por el ruido de fondo, sube `--rms`.
- Bajo cada respuesta aparecen sus latencias: ASR, primer token y primer audio.

Otros parámetros: `--level`, `--topic`, `--voice` (ruta a otra voz de Piper), `--max-tokens` (150), `--llm-url`, `--whisper-url` y `--port`.

## Resultados de la prueba automática (2026-11-20)

La prueba se hizo en la RTX 5060 Ti de la medición del banco, con Whisper large-v3-turbo, Qwen3-8B-Q4_K_M y Piper `lessac` en CPU. Un cliente WebSocket envió voz sintética (Piper `ryan`, 3,5–4,8 s), seguida de 1 s de silencio, en lugar del micrófono. Hubo tres corridas de tres turnos cada una, sin errores.

| Tramo | Apertura (sin caché previa) | Turnos del estudiante |
| --- | --- | --- |
| ASR | — | 99–282 ms |
| Primer token | 305–648 ms | 29–339 ms |
| Primer audio (desde el envío al LLM) | 376–715 ms | 101–539 ms |

- Whisper transcribió bien los turnos, salvo "I'm fine", que salió como "I'm Vine".
- El tutor respondió en tema con 2 o 3 frases y una pregunta. Una de las aperturas se salió del tema ("How did you hear about the app?"); puede deberse al mensaje oculto de apertura (`OPENING` en `server.py`).
- **Sin comprobar:** el uso en el navegador con micrófono real (captura, reproducción, eco y umbral de energía con ruido real).

## Prueba con Gemma 4 31B (2026-11-22)

Con la opción A, en el mismo equipo (2× RTX 5060 Ti, perfil `power-saver`).

- **Prueba automática:** apertura y dos turnos con voz sintética (Piper `ryan`), por WebSocket y sin errores.

  | Momento | ASR | Primer token | Primer audio (desde el envío al LLM) |
  | --- | --- | --- | --- |
  | Apertura, sin caché | — | 1360 ms | 1463 ms |
  | Apertura, con caché | — | 46 ms | 136 ms |
  | Turnos del estudiante | 110–113 ms | 81–96 ms | 172–242 ms |

- **Prueba manual en el navegador con micrófono real**, hecha por Nicolás: la conversación funcionó bien. No se midió de forma sistemática.
- **Sin comprobar:** otro equipo, ruido de fondo fuerte y sesiones largas cerca del límite de `-c 8192`.

## Prueba en Mac (opción C)

**Pendiente.** Los scripts se escribieron sin un Mac a mano: solo se revisó su sintaxis. No se ha comprobado ningún paso en un equipo real, y estas preguntas siguen abiertas:

- si el commit fijado de llama.cpp compila con Metal y soporta `--swa-full`, `-fa on` y el MTP del 12B en ese backend;
- cuánta memoria ocupa la configuración por defecto y si cabe sin subir `iogpu.wired_limit_mb`;
- la latencia real y la ganancia del MTP en el chip concreto.

Al probarlo, registra aquí el chip, la RAM, la versión de macOS, las variables usadas, la memoria que reporta `servidores-mac.sh` y la tabla de `bench.py`.
