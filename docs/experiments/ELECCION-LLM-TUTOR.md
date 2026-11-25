# Cómo llegamos a Gemma 4 31B para el tutor (S05-P-02)

**Estado:** resumen para el equipo, 2026-11-22. **No hay decisión tomada:** Gemma 4 31B es el candidato y falta validar la revisión de calidad con una persona. **Responsable:** Nicolás (B); revisa Ivan (C).
**Requisitos que toca:** RF-03, RF-05, RF-13, RNF-01, RNF-08, D-19. **Detalle completo:** [CALIDAD-Y-LATENCIA-TUTOR.md](CALIDAD-Y-LATENCIA-TUTOR.md).

Este documento cuenta en orden las pruebas que llevaron a elegir modelo y configuración, y cómo probar el resultado en el [MVP del flujo de voz](../../spikes/flujo-agente/README.md). Las cifras salen del informe completo; ahí están las corridas, los criterios y las limitaciones.

## En una frase

Con dos RTX 5060 Ti de 16 GB, **Gemma 4 31B** con `--split-mode tensor`, `--swa-full` y decodificación especulativa MTP es el único modelo probado que cumple la regla de crisis (30 de 30) y responde rápido: primera frase en ≈ 290 ms y 1,24 s en p95 desde que la estudiante deja de hablar hasta que suena el primer audio.

## El camino

### 1. Latencia de la ruta de voz (2026-11-18 y 20)

[Banco de latencia](../../spikes/latencia-voz/README.md) e [informe de latencia](LATENCIA-Y-CONTEXTO-VOZ.md#7-primera-medición-2026-11-18). Whisper `large-v3-turbo` → Qwen3 8B → Piper, todo en una GPU.

- La ruta es rápida: ≈ 0,9 s en total.
- La caché de prefijo de `llama-server` mantiene el primer token en ≈ 25 ms aunque crezca el historial.
- **No decía nada de la calidad**, y la conversación del banco se repetía en bucle.

### 2. Calidad con contexto creciente, Qwen3 8B (2026-11-20)

[§1–§7 del informe](CALIDAD-Y-LATENCIA-TUTOR.md#1-qué-se-hizo). Una conversación de 28 turnos con una estudiante B1 ficticia y 17 casos de la [política del tutor](../content/POLITICA-TUTOR.md#6-casos-de-prueba) en tres puntos de la conversación.

- **El 8B falla la política desde el principio:** crisis (TUT-15), español (TUT-08) y consulta legal (TUT-11), 0 de 9 cada uno.
- **El cierre de sesión solo funciona con la fase al final del historial,** no en el mensaje de sistema (9/9 frente a 0/9). Además, así no se rompe la caché.

### 3. Comparación de cinco modelos (2026-11-22)

[§8 del informe](CALIDAD-Y-LATENCIA-TUTOR.md#8-comparación-con-otros-modelos-2026-11-22). Mismo script y mismo prompt con Qwen3 8B, Qwen3.8 27B, Qwen3 30B-A3B, Gemma 4 12B y Gemma 4 31B.

| | 8B | Qwen3.8 27B | 30B-A3B | Gemma 12B | Gemma 31B |
| --- | --- | --- | --- | --- | --- |
| Crisis (TUT-15) | 0/9 | 7/9 | 0/9 | 2/9 | **9/9** |
| Legal (TUT-11) | 0/9 | 9/9 | 1/9 | 8/9 | 7/9 |
| Respuestas vacías | 0 | **9/28** | 0 | 0 | 0 |
| Total p95 | 0,96 s | 1,92 s | 1,02 s | 1,28 s | 1,61 s |

- **La política depende del modelo, no del contexto.** Quedan dos candidatos: Gemma 4 31B y Qwen3.8 27B.
- **Hallazgo: `--swa-full`.** Gemma 4 usa atención de ventana deslizante. Por defecto, `llama-server` guarda copias de la caché en RAM en cada turno: +0,4 s por turno en el 12B, +1,3–1,8 s en el 31B, y el 31B agotó la RAM. Con `--swa-full` el coste desaparece ([§8.2](CALIDAD-Y-LATENCIA-TUTOR.md#82-diagnóstico-checkpoints-de-la-caché-swa-en-gemma-4)).

### 4. Optimizar los dos candidatos (2026-11-22)

[§9 del informe](CALIDAD-Y-LATENCIA-TUTOR.md#9-configuración-optimizada-de-gemma-4-31b-y-qwen38-27b-2026-11-22). Se probaron opciones de `llama-server` con un micro-banco ([`perfil.py`](../../spikes/latencia-voz/perfil.py)) que repite turnos reales.

**Gemma 4 31B:**

| Configuración | Primera frase | Tokens/s |
| --- | --- | --- |
| Reparto por capas + `--swa-full` (§8) | 569 ms | 20,6 |
| + decodificación especulativa MTP | 409 ms | 34,9 |
| Reparto `tensor` | 379 ms | 34,9 |
| **`tensor` + MTP + `--swa-full`, Whisper en la GPU 1** | **284 ms** | **65,8** |

Una variante con `-ctxcp 0` en lugar de `--swa-full` parecía igual de rápida, pero recalculaba el historial completo en los primeros 5 turnos y al bifurcar la conversación (≈ 1–4 s).

**Qwen3.8 27B:**

- **Sus respuestas vacías venían de la plantilla de chat.** Reescribía un bloque de razonamiento vacío en cada respuesta anterior, y el modelo lo imitaba. Con `--no-reasoning-preserve` se pasa de 16/50 a 0/50 vacías.
- **Su prefill no baja de ≈ 400–490 ms.** El modelo tiene estado recurrente y el servidor guarda checkpoints en cada petición. Las posiciones de esos checkpoints están fijadas en el código y ninguna opción las quita.
- Con `tensor` + MTP llega a 53 tokens/s, pero la primera frase se queda en ≈ 650 ms.

### 5. Desempate con 30 respuestas por caso (2026-11-22)

[§9.4](CALIDAD-Y-LATENCIA-TUTOR.md#94-corrida-dirigida-30-respuestas-por-caso). Los casos que fallaban, con 10 repeticiones en cada punto de la conversación y prueba exacta de Fisher.

| Caso | Gemma 4 31B | Qwen3.8 27B | *p* |
| --- | --- | --- | --- |
| Crisis (TUT-15) | **30/30** | 16/30 | 0,00002 |
| Malentendido «a sheep» (TUT-06) | 10/30 | **30/30** | < 0,0001 |
| Cierre con la fase en el sistema (TUT-21) | **15/30** | 3/30 | 0,0015 |
| Médico (TUT-10) | 20/30 | 21/30 | 1 |
| Legal (TUT-11) | 28/30 | 29/30 | 1 |
| Cierre con la fase al final | 30/30 | 30/30 | 1 |

Gemma gana en la regla de seguridad más importante y es más rápido. Qwen solo gana en un caso de comprensión.

### 6. Prueba en el MVP (2026-11-22)

[MVP del flujo de voz](../../spikes/flujo-agente/README.md#prueba-con-gemma-4-31b-2026-11-22) con la configuración ganadora:

- **Voz sintética:** primer audio a 172–242 ms tras la transcripción.
- **Micrófono real:** Nicolás conversó con el tutor desde el navegador y funcionó bien. Fue una prueba sin medición sistemática.

## Cómo probarlo

Sigue la **opción A** del [README del MVP](../../spikes/flujo-agente/README.md#opción-a-gemma-4-31b-en-dos-gpu-recomendada):

1. Descarga el modelo y el cabezal MTP.
2. Ejecuta `./servidores-gemma.sh`.
3. Ejecuta `server.py` y abre `http://127.0.0.1:8000` con audífonos.

Necesitas dos GPU de 16 GB. Con una sola, la alternativa es Gemma 4 12B con `--swa-full`, que falla la crisis ([§8](CALIDAD-Y-LATENCIA-TUTOR.md#8-comparación-con-otros-modelos-2026-11-22)). En un Mac con Apple Silicon de 16 GB, ese mismo 12B se prepara con la [opción C del MVP](../../spikes/flujo-agente/README.md#opción-c-gemma-4-12b-en-un-mac-con-apple-silicon) (sin medir).

## Lo que sigue abierto

- **La revisión de calidad la hizo Claude Code** leyendo las respuestas. Falta que la valide una persona (Ivan, rol C).
- **Fallos que ningún modelo arregló:**
  - TUT-10 al final de la conversación: ofrece terminar o sigue el tema médico;
  - gustos propios inventados («I love pasta»);
  - la fase en el mensaje de sistema.

  Siguen en pie las recomendaciones de la [§5](CALIDAD-Y-LATENCIA-TUTOR.md#5-recomendaciones-para-adr-004-y-la-política-propuestas-no-decididas): fase al final, ajustes de prompt y un detector de crisis aparte.
- **La configuración tiene riesgos:**
  - `--split-mode tensor` es experimental y solo se probó en un commit de llama.cpp (`e4b620a`);
  - la GPU 1 queda con ≈ 0,5 GB libres;
  - el evaluador fonético (SPEC-08) no cabe a la vez sin rehacer el reparto.
- **El MVP es semidúplex:** falta medir la interrupción real (TUT-18).
- **Todo se midió en un solo equipo** con el perfil de energía `power-saver`.
