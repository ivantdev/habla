# Spike del canal de audio (S05-P-01)

**Estado:** prototipo y pruebas automáticas listos; **mediciones en navegador pendientes**. **Responsable:** Nicolás (B), con Sebastián (A) como custodio de C-04 y ADR-001. **Bloquea:** G0 (S05-P-01). **Código:** [spikes/audio-channel](../../spikes/audio-channel/README.md).

Objetivo: comprobar con un prototipo desechable que la propuesta de canal de [C-04](../architecture/CONTRACTS.md) funciona en el navegador antes de implementar ambos extremos. C-04 exige validar en este spike la conversión del navegador, el formato de salida del TTS y la cabecera de los frames.

## 1. Qué se comprueba

| Pregunta | Cómo se responde | Criterio para aceptarla en G0 |
| --- | --- | --- |
| ¿El navegador entrega PCM s16le mono 16 kHz en frames de 20 ms? | Prueba de tono: 1 kHz al micrófono → `dominant_hz` del servidor; WAV recibido | `dominant_hz` dentro de 1000 ± 10 Hz; el WAV se oye limpio |
| ¿Se pierden o desordenan frames? | `huecos` y `frames_invalidos` del servidor | 0 en `localhost` |
| ¿La cabecera de 56 bytes es correcta en ambos sentidos? | Pruebas automáticas y prueba en navegador | Pruebas en verde y ningún `unknown_frames` en el navegador |
| ¿El TTS se reproduce sin cortes? | `underruns` del navegador | 0 en `localhost` |
| ¿La interrupción detiene al tutor rápido? | `estimated_stop_ms` (inicio de la voz → parada estimada) | Se registra p50/p95; el límite lo fija G3 (S05-P-03, METRICS §7) |
| ¿Los frames tardíos de una generación cancelada se descartan? | `frames_tardios_descartados` frente a los simulados | Ninguna voz cancelada reaparece |
| ¿El eco del tutor dispara falsas interrupciones? | Prueba de silencio: interrupciones / generaciones | Decide si la demo exige auriculares o echoCancellation |

Las pruebas automáticas cubren solo el servidor: negociación, rechazo de perfil y de `Origin`, cabecera, huecos, duplicados e interrupción con frames tardíos. La captura, la reproducción y el detector de voz se verifican con el protocolo de la sección 2.

## 2. Protocolo

**Equipo:** registra en la sección 3 el PC, el sistema operativo, el micrófono, los auriculares o parlantes y la versión del navegador. La exportación incluye `user_agent` y los ajustes reales de la pista.

**Preparación:** instala el spike según su [README](../../spikes/audio-channel/README.md) y arranca `server.py`. Se prueba Chrome; Firefox y Edge, si da tiempo.

**Condiciones:** para cada combinación, abre una pestaña nueva con la URL indicada, pulsa «Comprobar micrófono», «Conectar canal» y «Medir RTT», ejecuta las repeticiones, pulsa «Estadísticas del servidor» y después «Exportar JSON». Guarda los JSON en una carpeta fuera del repositorio, por ejemplo `data/spike-audio/`.

| # | URL (`http://127.0.0.1:8000/?…`) | Repeticiones | Qué hacer |
| --- | --- | --- | --- |
| 1 | `salida=auriculares&prueba=interrumpir` | 20 | «Que hable el tutor»; a los 2–4 s, di una frase corta en voz normal |
| 2 | `salida=parlantes&prueba=interrumpir` | 20 | Igual que la 1 |
| 3 | `salida=parlantes&prueba=interrumpir&aec=0` | 20 | Igual que la 1 |
| 4 | `salida=auriculares&prueba=silencio` | 10 | «Que hable el tutor» y quedarse callado hasta que termine |
| 5 | `salida=parlantes&prueba=silencio` | 10 | Igual que la 4 |
| 6 | `salida=parlantes&prueba=silencio&aec=0` | 10 | Igual que la 4 |
| 7 | `salida=auriculares&prueba=tono` | 1 | Reproduce un tono de 1 kHz durante 5 s (desde el celular) junto al micrófono |

Deja «Frames tardíos simulados» en 10. El texto por defecto del tutor dura unos 20 s. Si el detector se dispara con el ruido ambiente, sube el margen del VAD y anótalo en «Nota de la prueba».

**Análisis:**

```powershell
cd spikes/audio-channel
.\.venv\Scripts\python.exe analizar.py ..\..\data\spike-audio
```

Pega la tabla en la sección 3. Escucha también un `out/recibido-*.wav` de la condición 1.

**Alcance de la medición:** 20 repeticiones bastan para decidir el canal en G0. La latencia de interrupción con al menos 100 turnos por configuración, en el PC de demo, corresponde a METRICS §7 y se mide con el producto en G1–G3.

## 3. Resultados

Pendiente de ejecutar el protocolo.

| Campo | Valor |
| --- | --- |
| Fecha | — |
| PC y sistema operativo | — |
| Navegadores y versiones | — |
| Micrófono y salida de audio | — |
| Commit del spike | — |

<!-- Tabla de analizar.py -->

Observaciones:

- —

## 4. Propuesta de cambios a C-04 y ADR-001

Para revisar con Sebastián (A) en el pull request de este spike; no se modifica C-04 hasta su aprobación. Se confirma solo lo que respalden los resultados de la sección 3.

1. **Entrada:** se confirma PCM s16le mono de 16 kHz en frames de 20 ms (640 bytes), convertido en el navegador con un `AudioWorklet` y filtro paso bajo.
2. **Cabecera de frame** (little-endian, 56 bytes): `version u8 | kind u8 (1 estudiante, 2 tutor) | reserved u16 | chunk_seq u32 | stream_id 16 B | turn_id 16 B | generation_id 16 B`. Los UUID ausentes van a cero. El receptor descarta frames con versión, tipo, `stream_id` o tamaño inesperados; los duplicados o desordenados no reescriben audio y los huecos no se rellenan.
3. **Salida del tutor:** PCM s16le mono a la frecuencia nativa del TTS (22 050 Hz con Piper `en_US-lessac-medium`) en frames de 20 ms. El servidor no remuestrea: `stream.ready` añade `output_sample_rate_hz` y el navegador crea los búferes a esa frecuencia.
4. **`stream.ready`** añade `output_sample_rate_hz`. `max_frame_bytes` = 56 + el mayor frame de entrada o salida (938 con los valores anteriores).
5. **`student.speech_started`** añade `interrupted_generation_id` y `heard_until_ms` (nulos si no sonaba el tutor). Con eso el servidor fija `heard_until_ms` de `tutor.interrupted` solo si coincide con la generación vigente; ADR-004 decide cómo se usa en el contexto del siguiente turno.
6. **Ritmo de envío del tutor:** el servidor no adelanta más de 200 ms de audio sobre el tiempo real, para que una interrupción deje poca salida en vuelo. El navegador añade 80 ms de colchón antes del primer frame de cada generación.
7. **`Origin`:** el handshake del canal se rechaza si `Origin` no pertenece al origen de la aplicación (`127.0.0.1`/`localhost` en los puertos 3000 y 8000 durante la iteración 1).

Fuera de esta propuesta: el detector de voz por energía del spike es provisional y se calibra en SPEC-05 (S05-P-03). Heartbeat y lease no se usan en la iteración 1 (C-09).
