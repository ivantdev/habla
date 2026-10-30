# Plan por iteraciones y reparto del equipo

**Estado:** acordado el 2026-10-30; fechas aproximadas por confirmar. **Fuentes:** [requisitos](REQUIREMENTS.md) (D-12 a D-17), [plan de specs](specs/README.md), [perfil de la iteración 1 (C-09)](architecture/CONTRACTS.md) y [métricas](experiments/METRICS.md).

El proyecto se presenta en formato *Shark Tank* en un auditorio de la universidad, aproximadamente mes y medio después del 2026-10-30. Este documento recorta el alcance en tres iteraciones y asigna el trabajo. Los requisitos conservan sus IDs.

**Autoridad:** las specs describen el comportamiento completo del producto. Este plan decide qué parte de cada spec se implementa en cada iteración y con qué mecanismos simplificados; el detalle técnico de la iteración 1 está en C-09 de los contratos. Si una spec exige algo que este plan difiere (cuentas, idempotencia, leases, recortes o caducidad), ese criterio se verifica en la iteración indicada aquí, no antes.

## Equipo

| Rol | Persona | Equipo de cómputo | Área |
| --- | --- | --- | --- |
| A | Sebastián | Sin GPU dedicada potente | Plataforma: backend, orquestación, audio y consentimiento, historial y comparación, cuentas y acceso a la demo |
| B | Nicolás | 2× RTX 5060 de 16 GB | Experiencia y voz: spike de audio, contenido, conversación, frases ancla, borrado y anotaciones humanas |
| C | Ivan | RTX 4090 y RTX 5090 en un mismo PC | Evaluación: experimentos, evaluador fonético, informe y métricas. Su PC es la máquina de la demo |

Todos desarrollan en `localhost`. Herramientas: Nicolás usa Claude Code; Sebastián e Ivan usan Codex. Las reglas comunes están en [AGENTS.md](../AGENTS.md).

## Criterios de aceptación por iteración (D-15)

Criterios de la [sección 8 de los requisitos](REQUIREMENTS.md). El pitch es el cierre de la iteración 2 (G3).

| Criterio | Iteración 1 (G2) | Pitch (G3) |
| --- | --- | --- |
| 1. Cuenta y práctica con voz | Práctica completa sin cuenta (usuario local) | Completo, con cuentas |
| 2. Interrumpir al tutor | Funciona; primera medición | Con el límite fijado tras medir |
| 3. Cinco anclas e informe | Completo | Completo |
| 4. Muestra recuperada y agotada | Completo | Completo |
| 5. Historial, audios y comparación | Completo para el usuario local | Completo por cuenta |
| 6. Borrado, caducidad y aislamiento | No incluido | Aislamiento entre cuentas obligatorio; borrado y caducidad si alcanza |
| 7. Micrófono, ocupado, fallos y recarga | Completo salvo reintento ante corte de canal (D-17) | Completo |
| 8. Mediciones y calidad pública | Métricas en validación | Prueba, líneas base y limitaciones |

Lo que no se cumpla en el pitch se declara explícitamente, sin presentarlo como terminado.

## Iteración 1 — MVP local (≈ 2026-10-30 a 2026-11-30)

**Objetivo:** un recorrido completo en el PC de Ivan, suficiente para saber qué funciona, qué sobra y qué es fundamental: elegir nivel, tema y duración → aceptar el consentimiento → conversar por voz con transcripción e interrupción → leer las cinco frases ancla con reintentos → recibir el informe → verlo en el historial y comparar dos sesiones por sonido.

### Incluye

| Requisito | Alcance en la iteración 1 |
| --- | --- |
| RF-01 | Cinco temas × tres niveles con fichas breves |
| RF-02, RF-03, RF-04, RF-05, RF-13, RF-15, RF-19 | Conversación completa: micrófono, tutor hablado, transcripción sin correcciones, temporizador de 5/10 min, interrupción y comprobación de micrófono |
| RF-06, RF-07, RF-17, RNF-14 | Evaluación fonética de las **frases ancla** (texto conocido), con dos reintentos por frase no evaluable |
| RF-08, RNF-04 | Informe en español: pronunciación desde anclas; gramática y vocabulario desde la transcripción con citas exactas. Declara que la pronunciación de la conversación no se evaluó |
| RF-09 (parcial) | Escuchar la propia frase ancla y su referencia estadounidense del catálogo |
| RF-10 (simple) | Consentimiento antes de grabar que describe lo que realmente ocurre en esta iteración (corpus del equipo, D-16) y menciona la Ley 1581 de 2012 |
| RF-12 (parcial), RNF-11 | Historial local: lista, informe, audios de anclas y comparación por sonido entre dos sesiones compatibles |
| RF-18 (parcial), RNF-10 | Un reintento manual ante fallo de modelo; una sola práctica activa (cupo hasta `processing`) |
| RNF-01, RNF-03 | Instrumentar latencias y medir el evaluador sobre **validación** |
| RNF-02, RNF-06, RNF-08, RNF-12, RT-01, RT-07 | Transversales: la evaluación no bloquea la charla, guía pedagógica, política y límites del tutor, interfaz en español, ruta ASR → LLM → TTS y datos públicos documentados |

### Simplificaciones de implementación

Resumen; el detalle está en C-09 de [CONTRACTS.md](architecture/CONTRACTS.md). Se conservan los DTO, los estados y `state_version` para trabajar en paralelo con fixtures y no romper nada en la iteración 2.

- **Usuario único local:** sin registro ni login. Todos los módulos usan un propietario local fijo (`owner_id` constante), así las cuentas de la iteración 2 no obligan a migrar datos.
- SQLite y una carpeta local para audio; tareas en segundo plano dentro del mismo proceso, sin cola externa.
- Sin `Idempotency-Key`, `deletion_epoch`, leases ni checkpoints de publicación. Antes de publicar un informe sí se comprueba `state_version` y que la práctica no esté cancelada.
- **Desviación aceptada de RF-18 (D-17):** si se cierra el canal o se recarga la página, la práctica pasa a `incomplete`. El reintento manual cubre los fallos de modelo; el reintento ante corte de conexión llega en la iteración 2.
- **Corpus del equipo (D-16):** las sesiones de los tres integrantes se conservan completas (audio, transcripciones, informe, evidencia y anclas) en `data/corpus/`, fuera del repositorio, para iterar y medir. Se registra qué integrante hizo cada sesión.
- Sin caducidad a 30 días ni borrado por el usuario. La evaluación fonética de la conversación libre y sus recortes quedan para la iteración 2.

### Reparto semanal

| Semana | Sebastián (A) | Nicolás (B) | Ivan (C) | Hito |
| --- | --- | --- | --- | --- |
| 1 (30 oct–6 nov) | Esqueleto FastAPI + React/Vite, SQLite, ADR-001; DTO y fixtures de C-08; propietario local fijo; **adaptadores simulados** de ASR, tutor, TTS y evaluador | **Spike de audio**; shell React; borrador de fichas; propuesta de cinco frases con Ivan | Verificar GPU (`nvidia-smi`, CUDA/PyTorch); descargar L2-ARCTIC y speechocean762; licencias y particiones por hablante; acceso a Azure | G0: stack, perfil de audio, DTO y perfil C-09 congelados |
| 2 (7–13 nov) | SPEC-04 mínimo: crear, iniciar, cancelar, reloj y cupo; SPEC-06: consentimiento, audio temporal y copia al corpus del equipo | SPEC-05: un turno real (VAD, Whisper, tutor LLM, TTS) en sus 5060; referencias habladas de las cinco frases con el TTS elegido (revisa Ivan) | wav2vec2 de fonemas + alineación + línea base GOP sobre validación; validador de anclas | G1: un turno hablado real |
| 3 (14–20 nov) | SPEC-04 completo según C-09: paso a anclas, `processing`, error y reintento, publicación; registro de latencias; validación de citas y del esquema del informe para SPEC-09 (revisa Ivan) | SPEC-05: conversación continua con interrupción y temporizador; SPEC-07: frases ancla con el validador de Ivan. El equipo empieza a acumular sesiones | Clasificador y umbral en validación (precisión ≥ 0,70); adaptador real para anclas; análisis de gramática y vocabulario con fixtures | — |
| 4 (21–30 nov) | Integración y arranque en el PC de Ivan; pruebas del recorrido; SPEC-10 historial y comparación | Vista de informe; guía de anotación con Ivan e inicio de anotaciones sobre el corpus | SPEC-09: informe con evidencia y citas verificadas; integración en su PC; primeras métricas en validación | G2: recorrido completo en el PC de Ivan |

Revisión al cerrar la iteración: qué funcionó, qué sobra y qué falta para el pitch. Ese resultado ajusta la iteración 2.

## Iteración 2 — Pitch, acceso y alcance (≈ 2026-12-01 a la presentación)

**Objetivo:** que la demo funcione en el auditorio, que varias personas puedan usar el producto y que el pitch tenga números reales.

| Prioridad | Trabajo | Requisitos | Responsable |
| --- | --- | --- | --- |
| P0 | Cuentas, inicio y cierre de sesión, aislamiento entre cuentas | RF-11, RNF-09 | Sebastián |
| P0 | Métricas finales en prueba, líneas base GOP y solo-transcripción, Azure si hay acceso, latencias y casos del tutor | RNF-01, RNF-03, RNF-08, RT-02 a RT-06 | Ivan; anotaciones, transcripción para WER y casos del tutor de Nicolás |
| P0 | Congelar el evaluador y grabar con esa versión las sesiones que se compararán en el pitch | RNF-11 | Ivan con Nicolás |
| P0 | Video del recorrido completo como respaldo | — | Nicolás |
| P0 | Análisis de despliegue en la nube: costo de GPU por hora y por sesión, arquitectura y escalado | D-13 | Sebastián |
| P0 | Decidir y preparar el acceso a la demo en el auditorio (ver abajo) | RNF-13 | Sebastián con Ivan |
| P1 | Reintento manual ante corte de canal e idempotencia de subidas (fin de D-17); obligatorio si la demo usa acceso por red | RF-17, RF-18 | Sebastián con Nicolás |
| P1, si alcanza | Borrado de sesiones, audios y cuenta; estado de audios; caducidad a 30 días | RF-16, RF-20, RNF-07 | Nicolás (SPEC-11) con Sebastián |
| P2 | Evaluación fonética en conversación libre con exclusión de palabras dudosas; recortes de error con referencia | RF-06, RF-09, RF-14, RNF-05 | Ivan con Sebastián |
| Después del pitch | Despliegue real en la nube | D-13 | Equipo |

### Acceso a la demo en el auditorio — decisión pendiente

Los PC con GPU están en las casas. Fuera de `localhost` el navegador solo permite el micrófono con HTTPS. Opciones:

1. **Red privada** (Tailscale sin Funnel): el portátil del auditorio entra a la red del equipo y usa HTTPS sin URL pública.
2. **Túnel público** (Cloudflare Tunnel o Tailscale Funnel): expone la app a internet; solo con cuentas activas y acceso restringido.
3. **Llevar el PC de Ivan** al auditorio y usar `localhost`.

Condiciones para cualquier opción:

- No exponer la app a internet sin autenticación.
- Probar la red del auditorio y la subida de internet de Ivan antes del ensayo.
- Tener siempre el video de respaldo.
- Si alguien del público prueba la app, el consentimiento describe la retención real. Sin caducidad implementada no se prometen 30 días, y el corpus del equipo (D-16) se desactiva para personas externas.

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
- Iteración 2: cuentas, reintento ante corte de canal, acceso a la demo, análisis de costos en la nube y material de negocio para el pitch.

Para ver el recorrido real con modelos, Sebastián prueba en el PC de Ivan o en el de Nicolás durante sesiones acordadas.
