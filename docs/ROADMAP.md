# Plan por iteraciones y reparto del equipo

**Estado:** acordado el 2026-10-30; fechas aproximadas por confirmar. **Fuentes:** [requisitos](REQUIREMENTS.md) (D-12 a D-14), [plan de specs](specs/README.md) y [métricas](experiments/METRICS.md).

El proyecto se presenta en formato *Shark Tank* en un auditorio de la universidad, aproximadamente mes y medio después del 2026-10-30. Este documento recorta el alcance en tres iteraciones y asigna el trabajo. Los requisitos conservan sus IDs; lo que cambia es **cuándo** y **con qué simplicidad** se implementa cada uno. Ante una contradicción, este plan decide el orden y las specs deciden el comportamiento.

## Equipo

| Rol | Persona | Equipo de cómputo | Área |
| --- | --- | --- | --- |
| A | Sebastián | Sin GPU dedicada potente | Plataforma: backend, orquestación, audio y consentimiento, historial y comparación, cuentas y acceso remoto |
| B | Nicolás | 2× RTX 5060 de 16 GB | Experiencia y voz: spike de audio, contenido, conversación, frases ancla, borrado y anotaciones humanas |
| C | Ivan | RTX 4090 y RTX 5090 en un mismo PC | Evaluación: experimentos, evaluador fonético, informe y métricas. Su PC es la máquina de la demo |

Todos desarrollan en `localhost`. Herramientas: Nicolás usa Claude Code; Sebastián e Ivan usan Codex. Las reglas comunes están en [AGENTS.md](../AGENTS.md).

## Iteración 1 — MVP local (≈ 2026-10-30 a 2026-11-30)

**Objetivo:** un recorrido completo en el PC de Ivan, suficiente para saber qué funciona, qué sobra y qué es fundamental: elegir nivel, tema y duración → aceptar el consentimiento → conversar por voz con transcripción e interrupción → leer las cinco frases ancla con reintentos → recibir el informe → verlo en el historial y comparar dos sesiones por sonido.

### Incluye

| Requisito | Alcance en la iteración 1 |
| --- | --- |
| RF-01 | Cinco temas × tres niveles con fichas breves |
| RF-02, RF-03, RF-04, RF-05, RF-13, RF-15, RF-19 | Conversación completa: micrófono, tutor hablado, transcripción sin correcciones, temporizador de 5/10 min, interrupción y comprobación de micrófono |
| RF-06, RF-07, RF-17, RNF-14 | Evaluación fonética de las **frases ancla** (texto conocido), con dos reintentos por frase no evaluable |
| RF-08, RNF-04 | Informe en español: pronunciación desde anclas; gramática y vocabulario desde la transcripción con citas exactas |
| RF-09 (parcial) | Escuchar la propia frase ancla y su referencia estadounidense del catálogo |
| RF-10 (simple) | Pantalla de consentimiento antes de grabar; menciona la Ley 1581 de 2012 |
| RF-12 (parcial), RNF-11 | Historial local: lista, informe, audios de anclas y comparación por sonido entre dos sesiones compatibles |
| RF-18 (simple), RNF-10 | Un reintento manual ante fallo; una sola práctica activa (cupo hasta `processing`) |
| RNF-01, RNF-03 | Instrumentar latencias y medir el evaluador sobre **validación** |

### Simplificaciones de implementación

Se conservan los DTO y estados de [CONTRACTS.md](architecture/CONTRACTS.md) para poder trabajar en paralelo con fixtures. Se simplifican los mecanismos:

- **Usuario único local:** sin registro ni login. Las cuentas pasan a la iteración 2. En esta iteración solo usan la app los integrantes del equipo.
- SQLite y una carpeta local para audio; tareas en segundo plano dentro del mismo proceso, sin cola externa.
- Sin `Idempotency-Key`, `deletion_epoch` ni checkpoints de publicación. Si se cierra el canal o se recarga la página, la práctica pasa a `incomplete` y se borra el audio temporal.
- El audio temporal se borra al publicar, cancelar o fallar. Aún no hay caducidad a 30 días ni borrado por el usuario.
- La evaluación fonética de la conversación libre y sus recortes quedan para la iteración 2.

### Reparto semanal

| Semana | Sebastián (A) | Nicolás (B) | Ivan (C) | Hito |
| --- | --- | --- | --- | --- |
| 1 (30 oct–6 nov) | Esqueleto FastAPI + React/Vite, SQLite, ADR-001; DTO y fixtures de C-08; **adaptadores simulados** de ASR, tutor, TTS y evaluador | **Spike de audio** (hoy); shell React; borrador de fichas; propuesta de cinco frases con Ivan | Verificar GPU (`nvidia-smi`, CUDA/PyTorch); descargar L2-ARCTIC y speechocean762; licencias y particiones por hablante; acceso a Azure | G0: stack, perfil de audio y DTO congelados |
| 2 (7–13 nov) | SPEC-04 mínimo: crear, iniciar, cancelar, reloj y cupo; SPEC-06: consentimiento y audio temporal | SPEC-05: un turno real (VAD, Whisper, tutor LLM, TTS) en sus 5060 | wav2vec2 de fonemas + alineación + línea base GOP sobre validación; validador de anclas | G1: un turno hablado real |
| 3 (14–20 nov) | SPEC-04 completo para la iteración: paso a anclas, `processing`, error y reintento, publicación; registro de latencias | SPEC-05: conversación continua con interrupción y temporizador; SPEC-07: frases ancla con el validador de Ivan | Clasificador y umbral en validación (precisión ≥ 0,70); adaptador real para anclas; esquema del informe | — |
| 4 (21–30 nov) | Integración y arranque en el PC de Ivan; pruebas del recorrido; SPEC-10 historial y comparación | Vista de informe; inicio de las anotaciones humanas (guía con Ivan) | SPEC-09: informe con citas verificadas; integración en su PC; primeras métricas | G2: recorrido completo en el PC de Ivan |

Revisión al cerrar la iteración: qué funcionó, qué sobra y qué falta para el pitch. Ese resultado ajusta la iteración 2.

## Iteración 2 — Acceso remoto, nube y alcance (≈ 2026-12-01 a la presentación)

**Objetivo:** que la demo funcione en el auditorio, que varias personas puedan usar el producto y que el pitch tenga números reales.

| Prioridad | Trabajo | Requisitos | Responsable |
| --- | --- | --- | --- |
| P0 para el pitch | Acceso remoto HTTPS al PC de Ivan, ensayo en el auditorio y video de respaldo | RNF-13 | Sebastián con Ivan |
| P0 para el pitch | Métricas finales en prueba, líneas base GOP y solo-transcripción, Azure si hay acceso, latencias | RNF-01, RNF-03, RT-02 a RT-06 | Ivan; anotaciones de Nicolás |
| P0 para el pitch | Análisis de despliegue en la nube: costo de GPU por hora y por sesión, arquitectura y escalado | D-13 | Sebastián |
| P1 | Cuentas, inicio y cierre de sesión, aislamiento entre cuentas | RF-11, RNF-09 | Sebastián |
| P1 | Borrado de sesiones, audios y cuenta; estado de audios; caducidad a 30 días | RF-16, RF-20, RNF-07 | Nicolás (SPEC-11) con Sebastián |
| P2 | Evaluación fonética en conversación libre con exclusión de palabras dudosas; recortes de error con referencia | RF-06, RF-09, RF-14, RNF-05 | Ivan con Sebastián |
| Después del pitch | Despliegue real en la nube | D-13 | Equipo |

### Demo en el auditorio

Los PC con GPU están en las casas. En el auditorio el navegador no corre en `localhost` del PC de Ivan, así que el micrófono exige HTTPS. Opciones, en orden de preferencia:

1. **Túnel HTTPS** (Cloudflare Tunnel o Tailscale Funnel) desde el PC de Ivan; un portátil en el auditorio abre la URL. Requiere probar la red del auditorio y la subida de internet de Ivan.
2. Llevar el PC de Ivan al auditorio y usar `localhost`.
3. **Siempre:** video grabado del recorrido como respaldo.

## V3 — Plus para después

Valor de producto, pero poco impacto en el pitch:

- Francés y alemán; mapa de vocales frente a hablantes nativos.
- Grabaciones propias con acento colombiano y ajuste del modelo; piloto longitudinal; línea base de monólogo.
- Verificación y recuperación de cuenta por correo.
- Varias sesiones simultáneas; reanudar tras recargar.
- Equivalencia entre versiones del evaluador para comparar sesiones antiguas.
- Ideas nuevas por evaluar, sin requisito asociado: app móvil y planes para instituciones o academias.

## Qué puede hacer Sebastián sin GPU

Casi toda la plataforma es CPU:

- Backend, base de datos, máquina de estados, reloj, cupo, consentimiento, almacenamiento y limpieza de audio (SPEC-00, SPEC-04, SPEC-06).
- **Adaptadores simulados** para que cualquiera ejecute la app sin GPU. Para probar con voz real a baja velocidad: Whisper `tiny`/`base` y Piper TTS funcionan en CPU; un LLM pequeño cuantizado corre lento pero sirve para probar el flujo.
- Pruebas de integración, registro de latencias, scripts de arranque e integración en el PC de Ivan.
- Historial y comparación (SPEC-10), asignado el 2026-10-30 para equilibrar la carga.
- Iteración 2: cuentas, acceso HTTPS, análisis de costos en la nube y material de negocio para el pitch.

Para ver el recorrido real con modelos, Sebastián prueba en el PC de Ivan o en el de Nicolás durante sesiones acordadas.
