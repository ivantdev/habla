# Spike del canal de audio

Prototipo desechable para [S05-P-01](../../docs/specs/SPEC-05-voice-conversation.md) y la propuesta de canal de [C-04](../../docs/architecture/CONTRACTS.md). No es código de producto: el canal real se reescribe en el backend de SPEC-00/05. Protocolo y resultados: [docs/experiments/SPIKE-AUDIO.md](../../docs/experiments/SPIKE-AUDIO.md).

Valida:

- La captura en el navegador y su conversión a PCM s16le mono de 16 kHz en frames de 20 ms (`static/capture-worklet.js`).
- La negociación `stream.open` → `stream.ready` y la cabecera binaria de 56 bytes de cada frame.
- La voz del tutor con Piper en CPU (22 050 Hz), enviada por generación.
- La interrupción local por energía, el descarte de frames tardíos y el rechazo por `Origin`.

## Instalación (Python 3.11)

Desde `spikes/audio-channel/`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m piper.download_voices en_US-lessac-medium --download-dir out/voices
```

`out/` está en `.gitignore`: la voz y los WAV recibidos no se suben al repositorio.

## Uso

```powershell
.\.venv\Scripts\python.exe server.py          # http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m pytest -q        # pruebas del servidor y del análisis
.\.venv\Scripts\python.exe analizar.py <carpeta-con-exportaciones-json>
```

Abre `http://127.0.0.1:8000` en el navegador; en `localhost` el micrófono funciona sin HTTPS. Los parámetros de URL `aec=0`, `ns=0`, `agc=0`, `salida`, `prueba` y `cond` preconfiguran la página para cada condición del protocolo; `profile=otro` fuerza el rechazo de perfil.

Al cerrar el canal, el servidor guarda el audio recibido en `out/recibido-<stream_id>.wav` e imprime sus estadísticas.

## Mensajes propios del spike

`spike.ping`/`spike.pong` (RTT), `spike.tutor_say` (hace hablar al tutor con un texto y `late_frames` simulados) y `spike.stats_request`/`spike.stats` son solo de este prototipo y no forman parte de C-04.
