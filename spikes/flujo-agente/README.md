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

Requiere `llama-server` en el puerto 8081 y `whisper-server` en el 8082, arrancados como en la [sección 3 de la replicación del banco](../latencia-voz/README.md#3-arrancar-los-servidores). También usa el entorno `~/modelos-habla/venv` de ese banco, al que se añaden FastAPI y Uvicorn:

```bash
uv pip install -p ~/modelos-habla/venv/bin/python -r requirements.txt
cd spikes/flujo-agente
~/modelos-habla/venv/bin/python server.py       # http://127.0.0.1:8000
```

Abre `http://127.0.0.1:8000`. En `localhost` el micrófono funciona sin HTTPS. Se recomienda usar audífonos: la cancelación de eco del navegador ayuda, pero con altavoces el tutor puede oírse a sí mismo al final de cada respuesta.

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
