# ADR-001 — Base local de la iteración 1

**Estado** · Implementado para simulación. Revisión de B/C pendiente para congelar G0 e integrar audio real.

**Alcance** · SPEC-00, S00-P-01, S05-P-01, C-01 a C-05, C-08 y C-09.

## Entorno y módulos

FastAPI con Python 3.12 sirve HTTP y WebSocket en `127.0.0.1:8000`. React y Vite sirven el cliente en `127.0.0.1:3000` y reenvían ambos protocolos bajo `/api/v1`. Se usa un origen local único desde el navegador, con validación de los orígenes loopback declarados en [config.py](../../habla/config.py). Los comandos y requisitos están en el [README](../../README.md).

SQLite proporciona una transacción de estado y un índice de reserva único. Audio conserva los bytes en un directorio privado. El backend ejecuta una sola instancia y lanza tareas asíncronas por práctica con versión de estado. Los adaptadores reales deberán ejecutar la inferencia bloqueante fuera del bucle de atención HTTP y WebSocket.

| Ubicación | Responsabilidad |
| --- | --- |
| [habla/](../../habla/) | A mantiene entrada, contratos, identidad base, orquestación, audio, validación del informe e historial. |
| [web/](../../web/) | Shell y pantallas para el recorrido simulado. Nicolás revisa su integración con router, conversación, anclas y vista de informe. |
| [contracts/](../../contracts/) | JSON Schema v1 generado desde los modelos de servidor y fixtures de plataforma para B/C. |
| [simulators.py](../../habla/simulators.py) | Sustitutos de ASR, tutor, TTS, validez, evaluador y borrador de informe. Sus resultados y latencias se identifican como simulados. |

El actor de C-09 usa un identificador estable y el consentimiento sembrado de desarrollo. D-18 reserva la voz real al equipo con su acuerdo escrito. La sesión web de cuentas se define con SPEC-03 en la iteración 2.

## Perfil de audio ensayado

Se usa la propuesta de [SPIKE-AUDIO §4](../experiments/SPIKE-AUDIO.md#4-propuesta-de-cambios-a-c-04-y-adr-001) para el recorrido sintético. Es el mismo perfil de entrada y cabecera probado por Nicolás.

| Parámetro | Fixture de integración |
| --- | --- |
| Entrada | `pcm16-v1`, PCM s16le mono a 16 kHz, 640 bytes cada 20 ms. |
| Salida | PCM s16le mono a 22 050 Hz en el fixture, 882 bytes cada 20 ms. Se publica `output_sample_rate_hz` en `stream.ready`. |
| Cabecera | 56 bytes little-endian. `version u8`, `kind u8` (1 estudiante, 2 tutor), `reserved u16` a cero, `chunk_seq u32`, `stream_id 16 B`, `turn_id 16 B`, `generation_id 16 B`. Se usan 16 bytes a cero para una generación ausente. |
| Negociación | Sobre C-04 con `stream_id: null` y `stream.open` como primer evento. `stream.ready` devuelve el ID, el perfil y un máximo de 938 bytes. Los campos de heartbeat y lease valen cero en C-09. |
| Interrupción | `student.speech_started` puede identificar la generación interrumpida y `heard_until_ms`. El servidor acota la marca al audio enviado de esa generación. El cliente descarta frames de generaciones anteriores. |
| Ritmo | El servidor simulado envía cada frame a intervalos de 20 ms y el cliente comienza con 80 ms de colchón. Se descartan duplicados y paquetes fuera de orden. Se registran huecos sin sintetizar muestras para rellenarlos. |
| Origen y demo | Se valida `Origin` en HTTP y en el saludo WS. La recomendación de usar auriculares con voz real procede de las mediciones de eco del spike. |

Los resultados del spike en Chrome respaldan el perfil de transporte. El cierre de G0/G1 con B/C comprueba la frecuencia del TTS elegido, la captura real con `AudioWorklet`, la reacción audible a interrupciones y el comportamiento al vencer el reloj, incluida la ventana de cierre de S04-P-01.
