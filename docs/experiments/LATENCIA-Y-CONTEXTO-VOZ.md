# Latencia y ventana de contexto de la ruta de voz (S05-P-02)

**Estado:** análisis con una primera medición en la RTX 5060 Ti (sección 7, 2026-11-18) y su revisión de validez (§7.5, 2026-11-20); **no hay decisión tomada**. Las cifras marcadas «estimación» salen de cálculos o de órdenes de magnitud y se sustituyen por mediciones antes de ADR-004. Solo las marcadas «medido» proceden de pruebas propias. **Fecha:** 2026-11-18. **Responsable:** Nicolás (B), con Ivan (C). **Spec:** [SPEC-05](../specs/SPEC-05-voice-conversation.md), preguntas S05-P-02 y S05-P-03.
**Requisitos que toca:** RF-03, RF-04, RF-05, RF-15, RNF-01, RNF-02, RNF-08, RT-01. **Relacionado:** [candidatos de modelos](CANDIDATOS-MODELOS-VOZ.md), [spike del canal de audio](SPIKE-AUDIO.md), [política del tutor](../content/POLITICA-TUTOR.md) (POL-05, POL-11, POL-12) y [métricas §7](METRICS.md).

**Fuera de alcance:** la calidad de la transcripción y la detección de errores fonéticos y gramaticales del estudiante se miden en flujos paralelos (SPEC-01, SPEC-08 y SPEC-09). Aquí solo se mide la latencia de los modelos y el tamaño del contexto.

Este documento analiza la ruta en cascada **ASR → LLM → TTS** que exige RT-01: de dónde sale la latencia de un turno, cómo se arma y cuánto ocupa el contexto del tutor, y qué medir para decidir. La sección 5 deja el marco para compararla con los modelos *voice-to-voice* (S2S) que analiza otro integrante, con los mismos criterios.

## 1. Recorrido de un turno

| Marca | Evento | Dónde se registra |
| --- | --- | --- |
| `t0` | Último frame con voz del estudiante | Servidor (VAD, a posteriori) |
| `t1` | El VAD declara el fin del turno (`t0` + espera de silencio) | Servidor |
| `t2` | Texto final del ASR | Servidor |
| `t3` | Primer token del LLM | Servidor |
| `t4` | Primera frase completa del LLM | Servidor |
| `t5` | Primer fragmento de audio del TTS | Servidor (`tts_first_audio_ms` del spike) |
| `t6` | Primer frame del tutor enviado por el canal | Servidor |
| `t7` | Primer audio audible en el navegador | Navegador |

**Latencia de respuesta (RNF-01) = `t7 − t0`.** METRICS §7 la define «desde el fin de la voz del estudiante (VAD)». Conviene precisar con Ivan que se mide desde `t0` y no desde `t1`: la espera de silencio es, según la estimación de la sección 2, el componente más grande, y medir desde `t1` la escondería.

```text
estudiante habla ─┐ t0
                  │ espera de silencio (endpointing)
                  └─ t1 ─ ASR final ─ t2 ─ prefill + 1.er token ─ t3 ─ 1.a frase ─ t4
                                                                              │
                                     t7 ← colchón 80 ms ← t6 ← canal ← t5 ← TTS 1.er fragmento
```

## 2. Presupuesto de latencia

### 2.1 Por componente

| Tramo | Qué lo determina | Valor | Origen |
| --- | --- | --- | --- |
| `t1 − t0` espera de silencio | Configuración del VAD; estudiantes L2 hacen pausas largas a mitad de frase | 500–1000 ms | Estimación; es un parámetro, no un coste de cómputo |
| `t2 − t1` ASR final | Modelo, GPU y si el ASR ya procesó el audio mientras el estudiante hablaba | 100–300 ms con Whisper `large-v3-turbo` en GPU para 3–8 s de audio | Estimación, por medir |
| `t3 − t2` prefill y primer token | Tokens nuevos que el LLM debe procesar; con caché de prefijo solo el último turno | 50–150 ms con caché; 1–3 s sin caché a 3000 tokens | Estimación, por medir (sección 3.3) |
| `t4 − t3` primera frase | Velocidad de decodificación × longitud de la primera frase (POL-05 la mantiene corta) | 150–350 ms para 10–20 tokens a 50–70 tokens/s con un 8B en 4 bits | Estimación, por medir |
| `t5 − t4` TTS, primer fragmento | Modelo y tamaño de la frase | **50–60 ms p50 con Piper en CPU** (M1) | Medido en el spike (`tts_first_audio_ms`) |
| `t7 − t5` canal y reproducción | Colchón de 80 ms del navegador; RTT local | ~85 ms | Medido en el spike (RTT p50 1,1–1,2 ms; colchón fijado en `app.js`) |

### 2.2 Dos escenarios

Suma de los tramos al final de una conversación de 10 minutos (unos 3000 tokens de contexto, sección 3.2). Ambos son **estimaciones** para ordenar el trabajo, no resultados.

| Tramo | Secuencial, sin optimizar | Con streaming y caché |
| --- | --- | --- |
| Espera de silencio | 800 ms | 600 ms |
| ASR final | 300 ms | 150 ms (ASR incremental durante el turno) |
| Prefill y primer token | 1500 ms (todo el contexto) | 100 ms (caché de prefijo) |
| Primera frase | 300 ms | 250 ms |
| TTS primer fragmento | 60 ms | 60 ms |
| Canal y colchón | 85 ms | 85 ms |
| **Total `t7 − t0`** | **≈ 3,0 s** | **≈ 1,25 s** |

La referencia de la propuesta es p95 < 2 s (RNF-01, no acordada como límite). El escenario secuencial no la cumpliría y empeora a medida que crece la conversación; el optimizado sí, con margen para la variación del p95. La diferencia está casi toda en dos decisiones: la **caché de prefijo** y la **espera de silencio**.

### 2.3 Palancas, por impacto estimado

1. **Caché de prefijo del LLM.** Reutiliza el estado ya calculado del prompt de sistema y del historial; cada turno solo procesa los tokens nuevos. Hace que la latencia no crezca con la duración de la charla. `llama.cpp` (servidor, `cache_prompt`) y vLLM (*automatic prefix caching*) la ofrecen; **verificar** el comportamiento con el modelo elegido. Exige que el prefijo no cambie entre turnos (sección 3.3).
2. **Espera de silencio por nivel.** Es el mayor tramo y es un compromiso: si es corta, el tutor interrumpe al estudiante que busca una palabra, lo que contradice el objetivo de que hable (POL-01); si es larga, la respuesta tarda. Propuesta: valor configurable por nivel (más largo en A2) y calibrado con el corpus del equipo (D-16), contando cortes prematuros además de la latencia.
3. **Arranque especulativo.** Lanzar ASR final y LLM tras un silencio corto (p. ej. 300 ms) y confirmar el turno al cumplirse la espera completa. Si el estudiante sigue hablando, se cancela la generación con el `generation_id` que ya usa el canal y no se reproduce nada. Esconde parte de la espera a cambio de cómputo desperdiciado; **por medir** cuánto se cancela.
4. **Streaming por frases LLM → TTS.** El TTS empieza con la primera frase mientras el LLM sigue generando. El canal ya envía audio por generación y frames de 20 ms (SPIKE-AUDIO §4).
5. **ASR incremental.** Además de reducir `t2 − t1`, da las transcripciones parciales que exige RF-04 (S05-CA-04). Whisper no es de streaming nativo: se emula reprocesando el audio acumulado o por ventanas (coste de GPU por medir); un ASR de streaming lo da directamente.
6. **Detalles que pesan:** desactivar el modo de razonamiento de los modelos que lo tienen (en Qwen3, `enable_thinking=False` o `/no_think`; si no, genera texto oculto antes de responder); mantener los modelos cargados (el spike ya precarga la voz); turnos cortos (POL-05).

### 2.4 Interrupción

La parada del tutor ya está medida en el spike: **p50 110 ms, p95 113–116 ms** con auriculares o parlantes con AEC. La cascada la resuelve en el navegador sin pasar por los modelos, así que no depende del ASR ni del LLM. El problema abierto es el eco con parlantes (8 de 10 falsas interrupciones con AEC), que corresponde al VAD (SPIKE-AUDIO §4, punto 8), no a la arquitectura.

## 3. Ventana de contexto del tutor

### 3.1 Qué entra

Según la sección 4 de la [política](../content/POLITICA-TUTOR.md): un mensaje de sistema (plantilla, guía de nivel, ficha y bloque de fase) y el historial de turnos `final` o `interrupted` como mensajes `user`/`assistant`. El tutor interrumpido entra recortado a lo oído (`heard_until_ms`) con `[interrupted]` (POL-12); el estudiante inaudible entra como `[inaudible]`.

### 3.2 Cuánto ocupa

| Parte | Tamaño | Origen |
| --- | --- | --- |
| Plantilla del prompt de sistema | 437 palabras | Contado sobre la política |
| Guía de nivel y ficha (restaurante, un nivel) | ~120–150 palabras | Contado a ojo sobre FICHAS.md |
| **Sistema total** | **~750–850 tokens** | Estimación con ~1,3 tokens por palabra en inglés; contar con el tokenizador elegido |
| Un intercambio (estudiante 10–30 palabras + tutor 25–45) | ~70–100 tokens con la plantilla de chat | Estimación |
| Intercambios por minuto | 2,5–3 (ciclo de 20–25 s: hablar, esperar, escuchar) | Estimación |
| **Contexto a los 5 min** | **~1800–2300 tokens** | Estimación |
| **Contexto a los 10 min** | **~2800–3500 tokens** | Estimación |

**Capacidad.** Los candidatos admiten bastante más: Qwen3 8B declara 32 768 tokens nativos y Llama 3.1, 128 000 (**verificar** en sus fichas). La conversación más larga ocupa alrededor de una décima parte de la ventana más pequeña, así que **el historial completo de POL-11 cabe sin recortes**. El recorte del punto 5 de la sección 4 de la política solo haría falta si la latencia medida lo exigiera, y con caché de prefijo no debería.

**Memoria.** La caché KV de Qwen3 8B en fp16 ocupa unos 144 KiB por token (36 capas × 8 cabezas KV × 128 × 2 × 2 bytes, según su `config.json` publicado; **verificar**). A 4000 tokens son ~0,6 GB, poco frente a los ~5 GB de los pesos en 4 bits.

### 3.3 Qué rompe la caché de prefijo

La caché solo sirve mientras el principio del contexto sea idéntico entre turnos. En la plantilla actual:

| Cambio | Efecto | Propuesta |
| --- | --- | --- |
| `{phase_instructions}` está al final del mensaje de sistema, **antes** del historial | Al pasar de `opening` a `conversation` y a `closing` se invalida todo el historial. El paso a `closing` ocurre con la charla más larga: la despedida pagaría el prefill completo (~1–3 s estimados) | Mover el bloque de fase a un mensaje de sistema **después** del historial. Se decide en ADR-004 y sube `tutor_policy_version` |
| Recortar el último turno del tutor tras una interrupción (POL-12) | Solo invalida ese último mensaje | Aceptable |
| Recortar el historial por antigüedad | Invalida todo lo que sigue al recorte en cada turno | No recortar (POL-11), coherente con la sección 3.2 |
| Generación especulativa cancelada (sección 2.3) | No entra al contexto | Descartar su texto y su caché |

### 3.4 Calidad de lo que entra

- **Errores del ASR.** El tutor responde a lo que transcribe el ASR, no a lo que dijo el estudiante. POL-07 cubre el caso incomprensible; un error verosímil («sheep» por «ship», TUT-06) pasa al contexto como si fuera cierto.
- **Texto oído tras una interrupción.** El TTS genera por frases, así que la conversación conoce la duración de cada frase enviada. Propuesta para ADR-004: cortar por frase completa según `heard_until_ms` y, dentro de la frase en curso, por proporción de caracteres; usar marcas por palabra solo si el TTS elegido las da (**verificar** en Piper y Kokoro).

## 4. Ubicación en GPU

| Equipo | Propuesta | Por qué |
| --- | --- | --- |
| PC de Nicolás (2× RTX 5060 Ti de 16 GB, comprobado con `nvidia-smi` el 2026-11-18) | ASR y LLM en una GPU; TTS en CPU (Piper) o en la misma GPU (Kokoro); la otra GPU libre para pruebas del evaluador | Con estimaciones de pesos (Whisper turbo ~1,6 GB en fp16, 8B en 4 bits ~5 GB, KV ~0,6 GB) la ruta cabe en una GPU de 16 GB |
| PC de demo de Ivan (RTX 4090 + RTX 5090) | Ruta conversacional en una GPU y evaluador fonético en la otra | Aísla físicamente RNF-02: el evaluador lento no compite por la GPU de la conversación (S05-CA-06) |

Las memorias se miden con picos reales (CANDIDATOS-MODELOS-VOZ §6, punto 2); la tabla solo comprueba que el orden de magnitud cabe.

## 5. Cascada frente a *voice-to-voice*

Un modelo S2S recibe el audio del estudiante y genera audio del tutor sin pasar por texto intermedio, o con texto interno no expuesto. Otro integrante analiza esos modelos. Esta sección deja los criterios comunes y lo que se espera de cada arquitectura **según su diseño**; la columna S2S es una hipótesis que su análisis debe confirmar o corregir con modelos concretos.

### 5.1 Restricción de requisitos

RT-01 pide «una ruta conversacional con reconocimiento de voz, modelo de lenguaje y síntesis» y es un requisito **Base**. Usar un S2S como ruta principal cambia el alcance: exige una decisión del equipo y actualizar los requisitos, no se decide dentro de S05-P-02. Además, RF-04 (transcripción visible) y el informe (citas literales, RNF-04) necesitan transcripción del estudiante con cualquier arquitectura, así que un S2S probablemente seguiría necesitando un ASR en paralelo.

### 5.2 Criterios

| Criterio | Cascada ASR → LLM → TTS | *Voice-to-voice* (hipótesis por confirmar) |
| --- | --- | --- |
| Latencia `t7 − t0` | ~1,25 s estimados con streaming y caché; la espera de silencio domina | Potencialmente menor: algunos modelos *full-duplex* no esperan a un fin de turno explícito |
| Naturalidad y prosodia | Limitada por el TTS; no oye el tono del estudiante | Mayor: puede reaccionar a entonación, ritmo y emoción |
| Interrupción y solapamiento | Parada medida en 110 ms p50; turnos alternos estrictos | Los modelos *full-duplex* gestionan solapamientos y asentimientos de forma nativa; el eco con parlantes sigue siendo un problema de captura |
| Control del tutor (RNF-08, POL-01 a POL-13) | Prompt de texto explícito, versionado y comprobable con los 22 casos TUT | Por verificar: la adherencia a instrucciones suele ser menor y más difícil de probar caso a caso |
| No corregir pronunciación (RF-05, POL-06) | El LLM no oye la pronunciación: solo ve texto | **Riesgo propio**: el modelo oye el acento y puede comentarlo o pedir repetir |
| Transcripción (RF-04) e informe (RNF-04) | Nativa: el texto existe en cada etapa | Requiere ASR aparte o la transcripción que exponga el modelo; comprobar que sea literal |
| Observabilidad (RNF-01) | Cada tramo se mide por separado (sección 1) | Una caja negra: solo `t7 − t0` |
| Modularidad | Se cambia un componente sin tocar los otros | Todo o nada |
| Ventana de contexto | ~3500 tokens de texto en 10 min (sección 3.2) | El audio cuesta mucho más: a 12,5 tokens/s por canal (frecuencia del códec Mimi de Moshi según su publicación; **verificar**) son 7500 tokens por canal en 10 min, antes del texto. Comprobar si la ventana del modelo cubre 10 minutos |
| Memoria de GPU | ~7–8 GB estimados, repartibles entre GPU y CPU | Por medir; con el evaluador cargado (RNF-02) |
| Errores en cadena | Un error del ASR llega al LLM como cierto | No hay ASR intermedio: entiende el audio directamente |
| Español en crisis (POL-10) | Depende de la voz del TTS (POL-10, dependencia en la política) | Por verificar |
| Modelos abiertos y licencias | Varias opciones con licencia documentada (CANDIDATOS-MODELOS-VOZ) | Por verificar; menos opciones abiertas |

### 5.3 Fortalezas de cada arquitectura

**Cascada:** control y verificación del comportamiento del tutor con texto; transcripción literal disponible para la pantalla y el informe; cada tramo medible y reemplazable; el LLM no oye la pronunciación, lo que protege RF-05 por construcción; contexto pequeño en texto; cumple RT-01 tal como está.

**Voice-to-voice:** latencia potencialmente menor y turnos más naturales (solapamientos, asentimientos); prosodia expresiva; no arrastra errores del ASR al entender al estudiante; una sola pieza que desplegar.

**Híbridos a considerar** (sin cambiar RT-01): traer a la cascada lo mejor del S2S mediante un detector de fin de turno semántico en lugar de solo silencio, un TTS más expresivo, o un LLM con entrada de audio que conserve la salida en texto hacia el TTS. Cada uno se mide con el mismo protocolo.

### 5.4 Qué conviene que mida el análisis S2S

Para que la comparación sea justa, en el mismo equipo y con las mismas definiciones:

1. `t7 − t0` desde el último frame con voz, con p50, p95 y máximo sobre al menos 100 turnos (METRICS §7).
2. Los 22 casos TUT de la política y la lista CHK, en especial TUT-05 y TUT-06 (no corregir) y TUT-15 (crisis en español).
3. Si el modelo expone una transcripción del estudiante y si es literal.
4. Memoria de GPU pico con el evaluador cargado.
5. Duración máxima de conversación que admite su ventana de contexto.
6. Licencia de pesos y código, y si corre en local o solo como API (un servicio externo exige explicarlo en el consentimiento, RF-10).

## 6. Recomendación y siguientes pasos

**Recomendación:** seguir con la cascada para la iteración 1. G1 (un turno hablado real) ya va retrasado según el [plan](../ROADMAP.md), RT-01 la exige y es la arquitectura que mejor protege RF-05 y el informe. El S2S se evalúa con los criterios de la sección 5 como alternativa para la iteración 2 o V3. Si sus mediciones lo justifican, el cambio de RT-01 se propone al equipo como decisión `D-xx`.

**Siguientes pasos:**

1. Instrumentar `t0`–`t7` en un banco de medición sobre las 5060 Ti con Whisper `large-v3-turbo`, un 8B en 4 bits y Piper o Kokoro, con y sin caché de prefijo, a 1, 5 y 10 minutos de historial simulado.
2. Barrer la espera de silencio (400–1000 ms) con grabaciones del equipo y contar cortes prematuros por nivel.
3. Acordar con Ivan que RNF-01 se mide desde `t0` (METRICS §7).
4. Proponer en ADR-004 mover el bloque de fase después del historial (sección 3.3) y la regla de texto oído (sección 3.4).

## 7. Primera medición (2026-11-18)

**Banco:** [spikes/latencia-voz](../../spikes/latencia-voz/README.md), 30 turnos por modo en una sola conversación simulada que crece turno a turno. **Detalle:** `spikes/latencia-voz/out/bench-20261118-223323.json` (no versionado). **Replicación:** commits de llama.cpp y whisper.cpp, sumas SHA-256 de los modelos y comandos exactos en el [README del banco](../../spikes/latencia-voz/README.md#replicación).

| Campo | Valor |
| --- | --- |
| Equipo | PC de Nicolás, RTX 5060 Ti de 16 GB (GPU 0; la GPU 1 sin uso), 24 hilos de CPU, 26 GB de RAM, Linux, controlador 595.99.02 |
| ASR | Whisper `large-v3-turbo` (ggml f16) en `whisper-server` de whisper.cpp `6680804`, CUDA sm_120, GPU 0 |
| LLM | Qwen3 8B `Q4_K_M` (GGUF oficial de Qwen) en `llama-server` de llama.cpp `e4b620a`, `-c 8192 -np 1 --jinja`, razonamiento desactivado, temperatura 0,7, GPU 0 |
| TTS | Piper 1.8.0 `en_US-lessac-medium` en CPU; Kokoro v1.0 ONNX (`kokoro-onnx` 0.6.1, voz `af_heart`) en CPU |
| Prompt | Plantilla de la política, B1, restaurante, fase `conversation`: 773 tokens de sistema |
| Audio del estudiante | 10 frases sintetizadas con Piper (voz `ryan`) a 16 kHz, de 1,8 a 5,4 s, en ciclo |
| Supuestos | Espera de silencio de 600 ms (parámetro) y canal de 85 ms (spike de audio) sumados a lo medido |

### 7.1 Resultados (ms)

| Tramo | Con caché p50 / p95 / máx | Sin caché p50 / p95 / máx |
| --- | --- | --- |
| ASR final (`t2 − t1`) | 99 / 120 / 121 | 100 / 119 / 122 |
| Primer token (`t3 − t2`) | **27 / 32 / 33** | **386 / 547 / 556** |
| Primera frase (`t4 − t3`) | 64 / 103 / 104 | 59 / 116 / 117 |
| TTS primer audio, Piper CPU (`t5 − t4`) | 40 / 73 / 96 | 42 / 65 / 178 |
| TTS primer audio, Kokoro CPU (`t5 − t4`) | 386 / 461 / 470 | 357 / 480 / 511 |
| **Total `t7 − t0` con Piper** | **928 / 976 / 983** | 1282 / 1472 / 1568 |
| Total `t7 − t0` con Kokoro | 1266 / 1371 / 1382 | 1606 / 1881 / 1896 |

| Dato | Valor |
| --- | --- |
| Contexto al turno 1 / 30 | 791 / 1967 tokens (≈ 40 tokens por intercambio) |
| Tokens nuevos por turno con caché | 18–59 |
| Prefill sin caché | ≈ 3700 tokens/s; el primer token crece ≈ 0,27 ms por token de contexto |
| Decodificación | 76–80 tokens/s |
| Memoria GPU 0 (Whisper + Qwen3 con contexto de 8192) | 7954 MiB de 16 311 |
| Texto de razonamiento (`<think>`) | Ninguno |

### 7.2 Lectura

- **Los modelos no son el cuello de botella.** Con caché, ASR + LLM + Piper suman ≈ 240 ms en p50; del total de 928 ms, 600 ms son la espera de silencio supuesta. La palanca principal es el fin de turno (sección 2.3, punto 2).
- **La caché de prefijo es necesaria.** Sin ella el primer token pasa de 27 ms a 386–556 ms y crece con la conversación; extrapolando 0,27 ms por token, a 3500 tokens serían ≈ 950 ms solo de prefill.
- **Las estimaciones de la sección 2 eran conservadoras:** ASR, prefill y decodificación resultaron más rápidos de lo estimado.
- **Kokoro en CPU** tarda ≈ 10 veces más que Piper. En GPU no se midió.
- **El contexto creció menos de lo estimado** (≈ 40 tokens por intercambio frente a 70–100), porque las frases del estudiante y las respuestas del tutor fueron cortas.

### 7.3 Limitaciones

- Audio del estudiante sintético y repetido: sirve para tiempos, no para la calidad del ASR.
- Primeras frases del tutor cortas (5 palabras de mediana, p. ej. «You're welcome!»); con frases más largas crecen `t4 − t3` y el TTS.
- Etapas medidas en secuencia y sin streaming del ASR; no se midió el arranque especulativo.
- Sin el evaluador fonético cargado en la GPU (RNF-02) y en una sola máquina; el PC de demo es el de Ivan.
- Una sola conversación por modo; en 100 turnos las frases del estudiante se repiten diez veces.

### 7.4 Corrida de 100 turnos

Misma configuración, 100 turnos por modo (el mínimo de METRICS §7). El contexto creció de 791 a ≈ 4900 tokens, más que una conversación de 10 minutos según la sección 3.2. **Detalle:** `spikes/latencia-voz/out/bench-20261118-223737.json`.

| Tramo (ms) | Con caché p50 / p95 / máx | Sin caché p50 / p95 / máx |
| --- | --- | --- |
| ASR final | 99 / 117 / 121 | 99 / 117 / 120 |
| Primer token | **33 / 39 / 41** | **805 / 1369 / 1432** |
| Primera frase | 61 / 107 / 112 | 74 / 133 / 140 |
| TTS Piper CPU | 35 / 70 / 146 | 43 / 74 / 78 |
| TTS Kokoro CPU | 355 / 442 / 493 | 372 / 464 / 501 |
| **Total con Piper** | **922 / 973 / 1072** | 1683 / **2276** / 2387 |
| Total con Kokoro | 1250 / 1338 / 1392 | 2015 / 2665 / 2806 |

Con caché, el primer token se mantiene en 33–41 ms hasta ≈ 4900 tokens: la latencia no depende de la duración de la charla. Sin caché, el p95 total con Piper (2,28 s) supera la referencia de 2 s de RNF-01. Memoria de la GPU 0: 7956 MiB.

### 7.5 Revisión de validez (2026-11-20)

Revisión de los JSON de ambas corridas, sin mediciones nuevas:

- **La caché se desactivó de verdad en el modo «sin caché»:** `cache_n` vale 0 en todos los turnos. En el modo con caché crece hasta 4876 tokens y cada turno procesa solo 18–59 tokens nuevos.
- **La conversación de 100 turnos entra en bucle.** Hay solo **10 primeras frases distintas en 100 turnos**, en ambos modos. Cuando el audio del estudiante se repite, Qwen3 repite su respuesta anterior. Por eso los p95 de la primera frase y del TTS salen, en la práctica, de 10 casos y no de 100.
- **Primeras frases cortas:** 4,5 palabras de mediana y 8 como máximo. Con frases de 12–20 palabras crecerían `t4 − t3` y, sobre todo, el TTS de Kokoro.
- **Medición en secuencia y sin carga paralela.** El banco no incluye el ASR incremental durante el turno, la decodificación del LLM mientras el TTS sintetiza ni el evaluador fonético en la GPU (RNF-02). El p95 real será mayor.
- **Audio de 5,2 s como máximo.** Un estudiante L2 puede hablar 10–15 s, y Whisper sin streaming procesa todo el clip al final del turno.
- **El historial empieza con el estudiante,** sin el saludo de apertura del tutor. No afecta a los tiempos, pero la conversación simulada es poco realista.

**Prueba de calidad y latencia (2026-11-20):** la conversación sin bucle y los casos TUT con contexto creciente están en [CALIDAD-Y-LATENCIA-TUTOR.md](CALIDAD-Y-LATENCIA-TUTOR.md). Confirma la latencia plana con caché y muestra que mover el bloque de fase después del historial también mejora la calidad del cierre.

**Siguientes medidas propuestas:** frases del estudiante variadas, para romper el bucle (hecho en la prueba de calidad); TTS sobre frases del tutor de longitud realista; Kokoro en GPU y en paralelo con la decodificación; una corrida con el evaluador cargado; y el barrido de la espera de silencio con grabaciones reales (sección 6, punto 2), que es el tramo mayor y sigue siendo un supuesto.
