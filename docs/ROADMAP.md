# Plan por iteraciones y reparto del equipo

**Estado:** acordado el 2026-10-30; fechas aproximadas por confirmar. **Fuentes:** [requisitos](REQUIREMENTS.md) (D-12 a D-18), [plan de specs](specs/README.md), [perfil de la iteración 1 (C-09)](architecture/CONTRACTS.md) y [métricas](experiments/METRICS.md).

El proyecto se presenta en formato *Shark Tank* en un auditorio de la universidad, aproximadamente mes y medio después del 2026-10-30. Este documento recorta el alcance en dos iteraciones y V3 y asigna el trabajo. Los requisitos conservan sus IDs.

**Autoridad:** las specs describen el comportamiento completo del producto. Este plan decide qué parte de cada spec se implementa en cada iteración y con qué mecanismos simplificados; el detalle técnico de la iteración 1 está en C-09 de los contratos. Si una spec exige algo que este plan difiere (cuentas, texto de consentimiento, idempotencia, leases, `deletion_epoch`, checkpoints, recortes, borrado o caducidad), ese criterio se verifica en la iteración indicada aquí, no antes.

## Equipo

| Rol | Persona | Equipo de cómputo | Área |
| --- | --- | --- | --- |
| A | Sebastián | Sin GPU dedicada potente | Plataforma: backend, orquestación, audio y consentimiento, historial y comparación, cuentas y acceso a la demo |
| B | Nicolás | 2× RTX 5060 de 16 GB | Experiencia y voz: spike de audio, contenido, conversación, frases ancla, borrado y anotaciones humanas |
| C | Ivan | RTX 4090 y RTX 5090 en un mismo PC | Evaluación: experimentos, evaluador fonético, informe y métricas. Su PC es la máquina de la demo |

Todos desarrollan en `localhost`. Herramientas: Nicolás usa Claude Code; Sebastián e Ivan usan Codex. Las reglas comunes están en [AGENTS.md](../AGENTS.md).

## Criterios de aceptación por iteración (D-15)

Criterios de la [sección 8 de los requisitos](REQUIREMENTS.md). El pitch es el hito G3 de la iteración 2; el despliegue en la nube cierra la iteración después del pitch (D-13).

| Criterio | Iteración 1 (G2) | Pitch (G3) |
| --- | --- | --- |
| 1. Cuenta y práctica con voz | Práctica completa sin cuenta (usuario base, D-18) | Completo, con cuentas |
| 2. Interrumpir al tutor | Funciona; primera medición | Con el límite fijado tras medir |
| 3. Cinco anclas e informe | Completo, con pronunciación desde las anclas | Completo; pronunciación de la conversación libre solo si se hace P2 |
| 4. Muestra recuperada y agotada | Completo, verificado con el modo corpus desactivado (C-09) | Completo |
| 5. Historial, audios y comparación | Completo para el usuario base (audios de anclas) | Completo por cuenta; recortes y audios vencidos solo si se hacen P1 y P2 |
| 6. Borrado, caducidad y aislamiento | No incluido | Aislamiento entre cuentas obligatorio; borrado y caducidad si alcanza |
| 7. Micrófono, ocupado, fallos y recarga | Completo salvo reintento ante corte de canal (D-17) | Completo |
| 8. Mediciones y calidad pública | Métricas en validación | Prueba, líneas base y limitaciones |

Lo que no se cumpla en el pitch se declara explícitamente, sin presentarlo como terminado.

## Iteración 1 — Versión local (≈ 2026-10-30 a 2026-11-30)

**Objetivo:** un recorrido completo en el PC de Ivan, suficiente para saber qué funciona, qué sobra y qué es fundamental: elegir nivel, tema y duración → conversar por voz con transcripción e interrupción → leer las cinco frases ancla con reintentos → recibir el informe → verlo en el historial y comparar dos sesiones por sonido.

### Incluye

| Requisito | Alcance en la iteración 1 |
| --- | --- |
| RF-01 | Cinco temas × tres niveles con fichas breves |
| RF-02, RF-03, RF-04, RF-05, RF-13, RF-15, RF-19 | Conversación completa: micrófono, tutor hablado, transcripción sin correcciones, temporizador de 5/10 min, interrupción y comprobación de micrófono |
| RF-06, RF-07, RF-17, RNF-14 | Evaluación fonética de las **frases ancla** (texto conocido), con dos reintentos por frase no evaluable |
| RF-08, RNF-04 | Informe en español: pronunciación desde anclas; gramática y vocabulario desde la transcripción con citas exactas. Declara que la pronunciación de la conversación no se evaluó |
| RF-09 (parcial) | Escuchar la propia frase ancla y su referencia estadounidense del catálogo |
| RF-12 (parcial), RNF-11 | Historial local: lista, informe, audios de anclas y comparación por sonido entre dos sesiones compatibles |
| RF-18 (parcial), RNF-10 | Un reintento manual ante fallo de modelo; una sola práctica activa (cupo hasta `processing`) |
| RNF-01, RNF-03 | Instrumentar latencias y medir el evaluador sobre **validación** |
| RT-03 | Particiones por hablante sin hablantes compartidos (semana 1) |
| RNF-02, RNF-06, RNF-08, RNF-12, RT-01, RT-07 | Transversales: la evaluación no bloquea la charla (se verifica con un evaluador lento simulado, S05-CA-06), guía pedagógica, política y límites del tutor, interfaz en español, ruta ASR → LLM → TTS y datos públicos documentados |

### Simplificaciones de implementación

Resumen; el detalle está en C-09 de [CONTRACTS.md](architecture/CONTRACTS.md). Se conservan los DTO, los estados y `state_version` para trabajar en paralelo con fixtures y no romper nada en la iteración 2.

- **Usuario base (D-18):** sin registro ni login. Todos los módulos usan una cuenta sembrada con `owner_id` constante, que se conserva en la iteración 2; así las cuentas no obligan a migrar datos.
- **Consentimiento (D-18):** la app no muestra texto de consentimiento. El usuario base tiene un consentimiento sembrado respaldado por el acuerdo escrito de los tres integrantes; el texto y el flujo de RF-10 llegan en la iteración 2.
- SQLite y una carpeta local para audio; tareas en segundo plano dentro del mismo proceso, sin cola externa. Al arrancar, las prácticas no terminales pasan a `incomplete` y se libera el cupo.
- Sin `Idempotency-Key`, `deletion_epoch`, leases ni checkpoints de publicación. Antes de publicar un informe sí se comprueba `state_version` y que la práctica no esté cancelada.
- **Desviación aceptada de RF-18 (D-17):** si se cierra el canal o se recarga la página, la práctica pasa a `incomplete`. El reintento manual cubre los fallos de modelo; el reintento ante corte de conexión llega en la iteración 2.
- **Corpus del equipo (D-16):** las sesiones de los tres integrantes se conservan completas (audio, transcripciones, informe, evidencia y anclas) en `data/corpus/`, fuera del repositorio, para iterar y medir. El modo corpus registra qué integrante hizo cada sesión en el manifiesto del corpus, no en los DTO. Los criterios de limpieza (criterio 4, S06-CA-06 y G2) se verifican con el modo desactivado. Alcance, plazo y ubicación están pendientes (D-16).
- Sin caducidad a 30 días ni borrado por el usuario. La evaluación fonética de la conversación libre y sus recortes quedan para la iteración 2.

### Reparto semanal

| Semana | Sebastián (A) | Nicolás (B) | Ivan (C) | Hito |
| --- | --- | --- | --- | --- |
| 1 (30 oct–6 nov) | Arranque FastAPI + proyecto React/Vite, SQLite, ADR-001; DTO de C-02 y fixtures de identidad, estado y audio (C-08); usuario base sembrado; **adaptadores simulados** de ASR, tutor, TTS y evaluador | **Spike de audio**; shell React (router y componentes compartidos); fixtures de catálogo y canal; borrador de fichas; propuesta de cinco frases con Ivan | Verificar GPU (`nvidia-smi`, CUDA/PyTorch); descargar L2-ARCTIC y speechocean762; licencias y particiones por hablante; acceso a Azure; fixtures de evidencia e informe (C-08) | G0: stack, perfil de audio, DTO y perfil C-09 congelados |
| 2 (7–13 nov) | SPEC-04 mínimo: crear, iniciar, cancelar, reloj y cupo; SPEC-06: audio temporal, consentimiento sembrado del usuario base (D-18) y copia al corpus del equipo | SPEC-05: un turno real (VAD, Whisper, tutor LLM, TTS) en sus 5060; referencias habladas de las cinco frases con el TTS elegido (revisa Ivan); guía fonética de RNF-06 con Ivan (S02-RF-05) | wav2vec2 de fonemas + alineación + puntuación GOP sobre validación; validador de anclas y su conjunto de validez, grabado con Nicolás (METRICS §3) | G1: un turno hablado real |
| 3 (14–20 nov) | SPEC-04 completo según C-09: paso a anclas, `processing`, error y reintento, publicación; reconciliación al arrancar; registro de latencias; validación de citas y del esquema del informe para SPEC-09 (revisa Ivan) | SPEC-05: conversación continua con interrupción y temporizador; SPEC-07: frases ancla con el validador de Ivan. El equipo empieza a acumular sesiones | Umbral GOP en validación (precisión ≥ 0,70); adaptador real para anclas; análisis de gramática y vocabulario con fixtures; SPEC-09 mínimo (anclas y citas) | — |
| 4 (21–30 nov) | Integración y arranque en el PC de Ivan; pruebas del recorrido; SPEC-10 historial y comparación; modo demo con fallos simulados para los criterios 4 y 7 | Vista de informe; casos del tutor (RNF-08, revisa Ivan); guía de anotación con Ivan e inicio de anotaciones sobre el corpus | SPEC-09 de la iteración 1 completo: evidencia y citas verificadas; integración en su PC; primeras métricas en validación | G2: recorrido completo en el PC de Ivan |

El evaluador de la iteración 1 es la puntuación GOP sobre fonemas de wav2vec2 alineados, con umbral elegido en validación; el clasificador entrenado de la propuesta pasa a la iteración 2.

Revisión al cerrar la iteración (G2): qué funcionó, qué sobra y qué falta para el pitch. Ese resultado ajusta la iteración 2. En esa revisión se deciden además el acceso al auditorio, las fechas del ensayo y de la prueba de red, el navegador y el equipo de la demo, la política de datos para personas externas y los responsables del material del pitch.

## Iteración 2 — Pitch, acceso y alcance (≈ 2026-12-01 a la presentación; la nube, al final)

**Objetivo:** que la demo funcione en el auditorio, que varias personas puedan usar el producto y que el pitch tenga números reales.

| Prioridad | Trabajo | Requisitos | Responsable |
| --- | --- | --- | --- |
| P0 | Cuentas, inicio y cierre de sesión, aislamiento entre cuentas; el usuario base se conserva (D-18) | RF-11, RNF-09 | Sebastián |
| P0 | Texto y flujo de consentimiento con la retención real de la iteración, citando la Ley 1581 de 2012 (D-18, S06-P-01) | RF-10 | Sebastián |
| P0 | Métricas finales en prueba del evaluador congelado, líneas base (GOP si se adopta el clasificador) y solo-transcripción, Azure si hay acceso, latencias y medición del tutor con sus casos | RNF-01, RNF-03, RNF-08, RT-02 a RT-06 | Ivan; anotaciones y transcripción para WER de Nicolás |
| P0 | Congelar el evaluador y grabar con esa versión las sesiones que se compararán en el pitch | RNF-11 | Ivan con Nicolás |
| P0 | Video del recorrido completo como respaldo | — | Nicolás |
| P0 | Audio en la sala: cancelación de eco, micrófono de diadema y prueba en el ensayo | RF-15 | Nicolás |
| P0 | Material del pitch: deck (problema, mercado y competencia, modelo de negocio, costos, métricas y limitaciones), guion de la demo, reparto de la presentación y ensayo general | — | Por asignar en G2 |
| P0 | Análisis de despliegue en la nube: costo de GPU por hora y por sesión, arquitectura y escalado | D-13 | Sebastián |
| P0 | Preparar el acceso a la demo decidido en G2 (ver abajo) | RNF-13 | Sebastián con Ivan |
| P0 | Reintento manual ante corte de canal e idempotencia de subidas (fin de D-17) | RF-17, RF-18 | Sebastián con Nicolás |
| P1 | Clasificador entrenado de la propuesta comparado con GOP en validación; se adopta solo si mejora | RNF-03, RT-02, RT-04 | Ivan |
| P1, si alcanza | Borrado de sesiones, audios y cuenta | RF-16 | Nicolás (SPEC-11) con Sebastián |
| P1, si alcanza | Estado de audios y caducidad a 30 días, con reloj controlado para mostrarla | RF-20, RNF-07 | Sebastián (SPEC-06) |
| P2 | Evaluación fonética en conversación libre con exclusión de palabras dudosas; recortes de error con referencia | RF-06, RF-09, RF-14, RNF-05 | Ivan con Sebastián |
| Al final, después del pitch | Despliegue real en la nube | D-13 | Equipo |

### Acceso a la demo en el auditorio — se decide en G2

Los PC con GPU están en las casas. Fuera de `localhost` el navegador solo permite el micrófono con HTTPS. Opciones:

1. **Red privada** (Tailscale sin Funnel): el portátil del auditorio entra a la red del equipo y usa HTTPS sin URL pública.
2. **Túnel público** (Cloudflare Tunnel o Tailscale Funnel): expone la app a internet; solo con cuentas activas y acceso restringido.
3. **Llevar el PC de Ivan** al auditorio y usar `localhost`.

Condiciones para cualquier opción:

- No exponer la app a internet sin autenticación.
- Probar la red del auditorio y la subida de internet de Ivan antes del ensayo.
- Tener siempre el video de respaldo.
- Si alguien del público prueba la app, el consentimiento describe la retención real. Sin caducidad implementada no se prometen 30 días, y el corpus del equipo (D-16) se desactiva para personas externas. La política de datos para personas externas (no conservar su audio o purgarlo al cerrar el evento) se decide en G2.

## V3 — Plus para después

Valor de producto, pero poco impacto en el pitch:

- Francés y alemán; mapa de vocales frente a hablantes nativos.
- Grabaciones con participantes externos y acento colombiano, ajuste del modelo, piloto longitudinal y línea base de monólogo.
- Verificación y recuperación de cuenta por correo.
- Varias sesiones simultáneas; reanudar tras recargar.
- Equivalencia entre versiones del evaluador para comparar sesiones antiguas.
- Ideas nuevas por evaluar, sin requisito asociado: app móvil y planes para instituciones o academias.

## Qué puede hacer Sebastián sin GPU

Casi toda la plataforma es CPU:

- Backend, base de datos, máquina de estados, reloj, cupo, consentimiento, almacenamiento, corpus del equipo y limpieza de audio (SPEC-00, SPEC-04, SPEC-06).
- **Adaptadores simulados** para que cualquiera ejecute la app sin GPU. Para probar con voz real a baja velocidad: Whisper `tiny`/`base` y Piper TTS funcionan en CPU; un LLM pequeño cuantizado corre lento pero sirve para probar el flujo.
- Validación de citas y del esquema del informe (SPEC-09, con Ivan), historial y comparación (SPEC-10).
- Pruebas de integración, registro de latencias, scripts de arranque e integración en el PC de Ivan.
- Iteración 2: cuentas, texto de consentimiento, caducidad, reintento ante corte de canal, acceso a la demo, análisis de costos en la nube y material de negocio para el pitch.

Para ver el recorrido real con modelos, Sebastián prueba en el PC de Ivan o en el de Nicolás durante sesiones acordadas.
