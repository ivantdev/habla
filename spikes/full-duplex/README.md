# Prueba local de Haru-4B

Candidato actual: [prueba de Sophon-Realtime 4B Flash](SOPHON.md), con interfaz
de micrófono e instrucciones personalizadas; [protocolo ampliado](../../docs/experiments/SOPHON-PROTOCOLO.md).
El ensayo de Haru tuvo resultado cualitativo insuficiente; se conserva como
evidencia y herramienta de diagnóstico.

Spike de Ivan para investigar una alternativa integrada de voz full duplex
(SPEC-01, S01-CA-05; S05-P-02 y S05-P-03). Protocolo, requisitos y registro de
evidencia: [FULL-DUPLEX.md](../../docs/experiments/FULL-DUPLEX.md).

Usa la demo oficial de Haru: micrófono → modelo integrado → voz. El reconocimiento
fonético APR se investigará por separado. Este spike no integra el modelo en el
producto ni sustituye el banco de cascada de Nicolás.

## Preparación

Linux, GPU NVIDIA con CUDA disponible, `uv`, Git y FFmpeg. La implementación
oficial estima unos 12 GB de VRAM; hay que medir el consumo real. Los pesos
descargados ocupan aproximadamente 10,5 GB, más entorno y cachés. Comprueba espacio
libre con `df -h .` antes de instalar.

Desde la raíz del repositorio:

```bash
nvidia-smi
bash spikes/full-duplex/setup.sh
bash spikes/full-duplex/run.sh
```

La preparación fija revisiones de código y pesos y las dependencias de
[requirements.txt](requirements.txt). Entorno, checkout externo, pesos y cachés
quedan en `data/full-duplex/`, excluido de Git. El arranque posterior usa los pesos
locales en modo offline.

La preparación instala también una voz sintética predeterminada a partir de la
[muestra oficial HEARME de Kokoro](https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff3571791e39611d31c381e3a41a3af07b4987/SAMPLES.md).
No hace falta grabar ni subir una voz personal. La referencia se descarga una
vez; Kokoro no se ejecuta durante la conversación. La muestra es inglesa y se
usa la misma al seleccionar inglés o español para mantener fija la referencia;
esto no demuestra todavía calidad de voz española. Su revisión, hash y duración
quedan en `data/full-duplex/reference/metadata.json`. Las referencias instaladas
previamente se conservan.

La GPU predeterminada es la 0 en orden PCI. Para seleccionar otra:

```bash
HARU_GPU=1 bash spikes/full-duplex/run.sh
```

El script acepta argumentos adicionales del servidor oficial. Por ejemplo,
`--language en` preselecciona inglés en una primera visita; el arranque usa
español por defecto. Una preferencia guardada por el navegador puede prevalecer:
selecciona el idioma explícitamente antes de empezar. Esto no prueba por sí solo
que la salida use ese idioma. `--codec-backend triton` cambia la configuración y exige
una medición separada de la ruta predeterminada PyTorch.

## Primer ensayo con micrófono

1. Abre <http://127.0.0.1:8998> y espera a que termine la carga y calentamiento.
2. Usa auriculares y micrófono por cable para la primera prueba.
3. Selecciona idioma, personaje y la voz predeterminada. Haru no distribuye una
   voz propia, pero este spike ya instala la referencia sintética. Grabar o subir
   otra voz es opcional. La referencia condiciona la voz del modelo, no es el
   audio de prueba del estudiante.
4. Prueba primero una charla breve en inglés, después otra en español y luego
   cambios entre ambos idiomas dentro de una conversación. Guarda el texto de
   la tarjeta de personaje y qué referencia se usó para poder repetirlo.
5. Comprueba pausas a mitad de frase e interrupciones según los casos del
   protocolo. Una impresión de fluidez no constituye una medición de latencia.

El servidor escucha en loopback, usa WebSocket y admite una sesión simultánea,
con límite de 15 minutos para permitir un ensayo de 10 minutos. Para detenerlo,
usa Ctrl+C en la terminal del servidor.

No se habilita el túnel público de la demo. No subas audios, referencias de voz
ni resultados con texto de la sesión a Git. `spikes/full-duplex/out/` también
está excluido; usa esa carpeta para artefactos de las pruebas.

## Comprobaciones del spike

```bash
bash -n spikes/full-duplex/setup.sh spikes/full-duplex/run.sh
python -m compileall -q spikes/full-duplex
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0 \
  XDG_CACHE_HOME="$PWD/data/full-duplex/cache" HF_HUB_OFFLINE=1 \
  data/full-duplex/venv/bin/python spikes/full-duplex/check_model.py
curl --fail http://127.0.0.1:8998/api/ready
```

La comprobación del modelo requiere los pesos y no debe ejecutarse a la vez que
el servidor: ambos cargarían una copia en GPU. Genera `out/check-model.json` y
dos WAV de 12 segundos con tarjetas en inglés/español, sin referencia de voz;
tras el bloque inicial introduce 89 bloques de silencio (11,87 s). Sirve para
verificar inferencia, salida finita, texto generado
y tiempo de cómputo; no prueba comprensión bilingüe ni voz representativa.

`ready: true` acredita carga y calentamiento. No acredita conversación bilingüe,
latencia audible, cumplimiento del tutor ni transcripción del estudiante.

## Tiempos de la conversación

La demo muestra estadísticas de retraso del flujo de audio y las envía al
servidor cada 10 segundos y al terminar. El arranque guarda la salida en
`spikes/full-duplex/out/server.log`, incluido p50/p95/mínimo/máximo cuando el
navegador envía las estadísticas. Puedes seguirlas con:

```bash
tail -f spikes/full-duplex/out/server.log
```

Ese indicador estima la separación entre el flujo del micrófono y el audio
reproducido, incluyendo búferes y latencias de dispositivos reportadas por el
navegador. No detecta el fin de cada intervención: no equivale al tiempo entre
terminar de hablar y oír una respuesta. Para la métrica de respuesta de METRICS
§7 hay que anotar esos eventos en una grabación o instrumentarlos por separado;
también queda pendiente medir la reacción a interrupciones.

## Diagnóstico de señal y voz

`run.sh` inicia la demo oficial mediante `diagnostic_server.py`, que mide cada
bloque inmediatamente antes de entregarlo a inferencia. Guarda nivel RMS en
dBFS, pico, finitud de las muestras y cómputo de cada bloque en
`out/signal-<id>.json`; también escribe resúmenes en `server.log` cada 10 s.
No guarda el audio ni el texto de la conversación. La energía no identifica voz
humana ni prueba reconocimiento; permite detectar silencio o nivel muy bajo.
La generación del modelo y el transporte oficial se conservan.

Para comprobar la ruta con una señal conocida, con el servidor listo y sin una
conversación manual activa:

```bash
data/full-duplex/venv/bin/python spikes/full-duplex/probe_transport.py
```

Envía silencio/voz sintética/silencio por Opus y WebSocket, en una ráfaga; no
mide conversación ni latencia real. Produce `out/websocket-probe.json` y el
diagnóstico de señal del servidor.

Para aislar el códec de la generación del conversador, fuera de las mediciones
de rendimiento:

```bash
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=0 \
  XDG_CACHE_HOME="$PWD/data/full-duplex/cache" HF_HUB_OFFLINE=1 \
  data/full-duplex/venv/bin/python spikes/full-duplex/check_codec.py
```

Carga solo los pesos del códec y reconstruye la referencia sintética por bloques,
usando las medias latentes sin añadir ruido. Produce
`out/codec-reference-original.wav` y `out/codec-reference-roundtrip.wav`. Hay que
compararlos auditivamente: salida finita no equivale a inteligibilidad.

## STT de grabaciones privadas de Haru

`transcribe_recordings.py` separa los canales del WebM oficial (izquierdo:
usuario; derecho: modelo) y usa Whisper localmente para diagnóstico. Requiere
descargar previamente el modelo, una sola vez:

```bash
data/full-duplex/venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("openai/whisper-large-v3-turbo",
    revision="41f01f3fe87f28c78e2fbf8b568835947dd65ed9",
    local_dir="data/full-duplex/whisper-turbo",
    allow_patterns=["*.json", "*.txt", "*.safetensors"])
PY
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 \
  data/full-duplex/venv/bin/python spikes/full-duplex/transcribe_recordings.py
```

Procesa `out/haru audio*.webm` y escribe `.asr.txt` y `.asr.json` junto a ellos.
Son datos privados, excluidos de Git. No sube audio a servicios externos.
Usa ventanas independientes de 20 s, idioma automático y tiempos aproximados.
Puede inventar palabras en silencio, audio débil o voz ininteligible: no usar
esos tramos como evidencia de idiomas, calidad ni latencia por turno. No calcula
WER sin referencia humana.
