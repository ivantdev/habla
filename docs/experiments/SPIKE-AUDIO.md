# Spike del canal de audio (S05-P-01)

**Estado:** prototipo, pruebas automáticas y mediciones en Chrome completas (7 condiciones); resultados en la sección 3, pendiente de revisión con Sebastián. **Responsable:** Nicolás (B), con Sebastián (A) como custodio de C-04 y ADR-001. **Bloquea:** G0 (S05-P-01). **Código:** [spikes/audio-channel](../../spikes/audio-channel/README.md).

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
| 7 | `salida=auriculares&prueba=tono&aec=0&ns=0&agc=0` | 1 | Reproduce un tono de 1 kHz durante 5–10 s (desde el celular) junto al micrófono integrado, sin pulsar «Que hable el tutor». Con los filtros del navegador activos, la supresión de ruido borra el tono y `dominant_hz` no es válido; comprueba en el JSON que `echoCancellation`, `noiseSuppression` y `autoGainControl` sean `false` |

Deja «Frames tardíos simulados» en 10. El texto por defecto del tutor dura unos 20 s. Si el detector se dispara con el ruido ambiente, sube el margen del VAD y anótalo en «Nota de la prueba».

**Análisis:**

```powershell
cd spikes/audio-channel
.\.venv\Scripts\python.exe analizar.py ..\..\data\spike-audio
```

Pega la tabla en la sección 3. Escucha también un `out/recibido-*.wav` de la condición 1.

**Alcance de la medición:** 20 repeticiones bastan para decidir el canal en G0. La latencia de interrupción con al menos 100 turnos por configuración, en el PC de demo, corresponde a METRICS §7 y se mide con el producto en G1–G3.

## 3. Resultados

| Campo | Valor |
| --- | --- |
| Fecha | 2026-11-08 |
| PC y sistema operativo | MacBook Pro (M1), macOS 26.7.2 |
| Navegadores y versiones | Chrome 156.0.8078.81 (Firefox y Edge no probados) |
| Micrófono y salida de audio | Condiciones 1 y 4: micrófono de los auriculares con cable («Micrófono externo»). Condiciones 2, 3, 5, 6 y 7: micrófono integrado del MacBook Pro. Salida: auriculares con cable o altavoces del Mac, según la condición |
| Commit del spike | 85e91cf, con la fila 7 del protocolo corregida (sin commit) |

Tabla de `analizar.py` sobre las siete exportaciones válidas. `dominant_hz` solo se evalúa en la prueba de tono; en las demás es la voz o el zumbido de fondo y se omite.

| # | salida | aec | prueba | generaciones | interrupciones | falsas por generación | parada p50 / p95 (ms) | primer audio p50 (ms) | underruns | huecos | frames inválidos | `dominant_hz` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | auriculares | sí | interrumpir | 20 | 20 | – | 110 / 113 | 59 | 0 | 0 | 0 | – |
| 2 | parlantes | sí | interrumpir | 21 | 21 | – | 110 / 116 | 50 | 0 | 0 | 0 | – |
| 3 | parlantes | no | interrumpir | 14 | 12 | – | 101 / 102 (cortes del propio eco) | 50 | 0 | 0 | 0 | – |
| 4 | auriculares | sí | silencio | 9 | 0 | 0,00 | – | 54 | 0 | 0 | 0 | – |
| 5 | parlantes | sí | silencio | 10 | 8 | 0,80 | – | 60 | 0 | 0 | 0 | – |
| 6 | parlantes | no | silencio | 15 | 14 | 0,93 | – | 51 | 0 | 0 | 0 | – |
| 7 | auriculares | no | tono | – | – | – | – | – | 0 | 0 | 0 | 998,5 |

RTT p50 de 1,1–1,2 ms y p95 de 1,8–2,6 ms en todas las condiciones. Ningún JSON registra `unknown_frames`.

**Contra los criterios de la sección 1**

| Pregunta | Resultado |
| --- | --- |
| PCM s16le mono 16 kHz en frames de 20 ms | Cumple: tono de 1 kHz recibido a 998,5 Hz (criterio 1000 ± 10 Hz) con los filtros del navegador desactivados |
| Pérdida o desorden de frames | Cumple: 0 huecos y 0 frames inválidos en las siete condiciones, en `localhost` |
| Cabecera de 56 bytes | Cumple: 0 `unknown_frames` y 0 frames inválidos. Rechazo de perfil y de `Origin` solo verificados por las pruebas automáticas |
| TTS sin cortes | Cumple: 0 `underruns` en las siete condiciones |
| Parada del tutor al interrumpir | Se registra: p50 110 ms y p95 113–116 ms con auriculares y con parlantes + AEC (20 y 21 repeticiones). El límite lo fija G3 (S05-P-03) |
| Frames tardíos de una generación cancelada | Cumple: se descartaron 206 (cond. 1) y 214 (cond. 2) frente a 10 simulados por interrupción, más los que ya iban en vuelo; ninguna voz cancelada reapareció |
| El eco del tutor dispara falsas interrupciones | **No cumple con parlantes.** Auriculares: 0 de 9. Parlantes con AEC: 8 de 10. Parlantes sin AEC: 14 de 15, siempre a ~0,2 s |

Observaciones:

- Con parlantes, el AEC de Chrome reduce el eco pero no basta para el detector por energía del spike: 8 de 10 generaciones se cortaron solas, entre 0,7 s y 9,8 s. Sin AEC se cortan casi todas a ~0,2 s. Con auriculares, ninguna.
- En la condición 6, la primera generación se completó y las 14 siguientes se cortaron; el detector parte de un ruido de fondo inicial que se ajusta con el tiempo. No se verificó la causa.
- La condición 3 es una medición de eco: las interrupciones son del propio tutor, no del estudiante, por lo que su parada p50 no es comparable con las condiciones 1 y 2.
- Las condiciones 1 y 4 usaron el micrófono de los auriculares y las demás el integrado del Mac, así que no se puede aislar el efecto del micrófono del de la salida. La parada p50 coincide en ambas (110 ms).
- La condición 4 tiene 9 generaciones, porque una repetición se solapó con la anterior.
- Una primera tanda de las condiciones 1 y 2, y un primer intento de la 3 y de la 7, se descartaron: se hicieron con el micrófono del iPhone (Continuidad) o con la supresión de ruido activa, que borra un tono puro. La fila 7 del protocolo se corrigió para añadir `aec=0&ns=0&agc=0`.
- Las condiciones se midieron con un solo navegador, un solo equipo y una persona hablando; los datos describen el canal, no la población de usuarios.

## 4. Propuesta de cambios a C-04 y ADR-001

Para revisar con Sebastián (A) en el pull request de este spike; no se modifica C-04 hasta su aprobación. Se confirma solo lo que respalden los resultados de la sección 3: cada punto indica su respaldo.

1. **Entrada:** se confirma PCM s16le mono de 16 kHz en frames de 20 ms (640 bytes), convertido en el navegador con un `AudioWorklet` y filtro paso bajo. *Respaldo:* tono a 998,5 Hz, 0 huecos y 0 frames inválidos.
2. **Cabecera de frame** (little-endian, 56 bytes): `version u8 | kind u8 (1 estudiante, 2 tutor) | reserved u16 | chunk_seq u32 | stream_id 16 B | turn_id 16 B | generation_id 16 B`. Los UUID ausentes van a cero. El receptor descarta frames con versión, tipo, `stream_id` o tamaño inesperados; los duplicados o desordenados no reescriben audio y los huecos no se rellenan. *Respaldo:* 0 `unknown_frames` en el navegador; descartes verificados por las pruebas automáticas.
3. **Salida del tutor:** PCM s16le mono a la frecuencia nativa del TTS (22 050 Hz con Piper `en_US-lessac-medium`) en frames de 20 ms. El servidor no remuestrea: `stream.ready` añade `output_sample_rate_hz` y el navegador crea los búferes a esa frecuencia. *Respaldo:* 0 `underruns` en las siete condiciones.
4. **`stream.ready`** añade `output_sample_rate_hz`. `max_frame_bytes` = 56 + el mayor frame de entrada o salida (938 con los valores anteriores).
5. **`student.speech_started`** añade `interrupted_generation_id` y `heard_until_ms` (nulos si no sonaba el tutor). Con eso el servidor fija `heard_until_ms` de `tutor.interrupted` solo si coincide con la generación vigente; ADR-004 decide cómo se usa en el contexto del siguiente turno. *Respaldo:* 41 interrupciones con `heard_until_ms` y `interrupted_generation_id` registrados.
6. **Ritmo de envío del tutor:** el servidor no adelanta más de 200 ms de audio sobre el tiempo real, para que una interrupción deje poca salida en vuelo. El navegador añade 80 ms de colchón antes del primer frame de cada generación. *Respaldo:* parada p50 de 110 ms, p95 de 113–116 ms, y los frames tardíos se descartaron.
7. **`Origin`:** el handshake del canal se rechaza si `Origin` no pertenece al origen de la aplicación (`127.0.0.1`/`localhost` en los puertos 3000 y 8000 durante la iteración 1). *Respaldo:* solo pruebas automáticas.
8. **Requisito de la demo (nuevo):** con altavoces, ni el AEC de Chrome ni un detector por energía evitan que el tutor se interrumpa solo (8 de 10 con AEC; 14 de 15 sin él). Con auriculares fueron 0 de 9. La demo de la iteración 1 debe usar auriculares, o el detector de voz de SPEC-05 debe resolver el eco antes de depender de altavoces. *Respaldo:* condiciones 4, 5 y 6.

Fuera de esta propuesta: el detector de voz por energía del spike es provisional y se calibra en SPEC-05 (S05-P-03). Heartbeat y lease no se usan en la iteración 1 (C-09).
