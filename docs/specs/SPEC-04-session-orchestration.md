# SPEC-04 — Sesiones, reloj, cupo y recuperación

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Orquestación  
> **RF relacionados:** RF-01, RF-13, RF-18 | **RNF:** RNF-01, RNF-09, RNF-10, RNF-12  
> **RT:** No aplica directamente  
> **Módulo:** Orquestación | **Responsable:** A; B integra estados y C trabajos  
> **Etapa:** E1 mínimo; E2 completo | **Iteración:** 1 con el perfil C-09; lease, idempotencia y reintento ante corte de canal en la 2 | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

Una sesión combina voz, frases y procesamiento, con una sola práctica activa en la demo. Un orquestador único evita que cada módulo interprete distinto el tiempo, la finalización o los fallos.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existe máquina de estados, reloj, bloqueo de cupo ni recuperación. Los estados y operaciones de architecture/C-03 son una propuesta que debe materializarse con persistencia y concurrencia verificables.

## 3. Historia de usuario

> Como estudiante, quiero saber en qué etapa está mi práctica y recuperarme de un fallo permitido sin recibir un informe de una sesión incompleta.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro del alcance de la spec

- Creación y snapshot, inicio, tiempo 5/10 minutos, transición a frases y procesamiento.
- Cupo atómico, cancelación, abandono, un reintento manual por incidente y terminales coherentes.
- Control de versiones, publicación coordinada y descarte de resultados tardíos.

### Fuera del alcance de la spec

- Cola de espera de estudiantes, prácticas simultáneas y reanudación después de recarga.
- Algoritmos ASR, fonéticos o lingüísticos que pertenecen a otros módulos.

### Supuestos acordados

- Confirmados: duración desde inicio de charla, pausas incluidas, un reintento manual y recarga sin reanudación. El cupo se reserva hasta terminar el procesamiento (decidido el 2026-10-30).

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S04-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S04-RF-01** (RF-01, RNF-10) — CUANDO un propietario solicite una práctica con configuración y consentimiento vigentes y exista cupo, EL SISTEMA DEBE crear una única práctica ready con snapshot de contenido y reservar el cupo atómicamente.
- **S04-RF-02** (RNF-10) — MIENTRAS el servidor tenga una práctica activa que ocupe el cupo, EL SISTEMA DEBE rechazar otra práctica sin impedir consultar el historial.
- **S04-RF-03** (RF-13) — CUANDO comience la charla, EL SISTEMA DEBE fijar una sola vez el inicio y el vencimiento a 300 o 600 segundos y avanzar a frases al vencer sin abrir más turnos conversacionales.
- **S04-RF-04** (RF-13, RF-18) — CUANDO el propietario cancele o se detecte abandono de la página, EL SISTEMA DEBE marcar la práctica incompleta, impedir publicación y ordenar revocación y eliminación del audio temporal.
- **S04-RF-05** (RF-18) — SI falla una conexión o un modelo recuperable, ENTONCES EL SISTEMA DEBE informar la operación fallida y ofrecer un único reintento manual dentro de la página activa.
- **S04-RF-06** (RF-18; derivado de RF-08) — CUANDO todos los requisitos de publicación y limpieza estén confirmados, EL SISTEMA DEBE hacer visible el informe y el estado completed mediante una operación consistente.
- **S04-RF-07** (RF-18, RNF-10) — SI llega un comando duplicado o con una versión de estado obsoleta, ENTONCES EL SISTEMA DEBE devolver el resultado idempotente o un conflicto sin repetir efectos.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S04-CA-01** (S04-RF-01) — Dados dos propietarios que inician simultáneamente y una clave repetida del primero, Cuando se resuelvan las solicitudes, Entonces solo una reserva existe, el segundo recibe SERVER_BUSY y la repetición no crea otra práctica.
- [ ] **S04-CA-02** (S04-RF-02) — Dada una práctica activa, Cuando otro estudiante consulte su historial y solicite iniciar, Entonces la consulta funciona y el inicio muestra servidor ocupado con opción de reintentar.
- [ ] **S04-CA-03** (S04-RF-03) — Dado un reloj controlado con pausas y error temporal, Cuando se alcance el vencimiento de ambas duraciones, Entonces se detiene salida/captura conversacional, se cierran turnos y se entra en anchors sin reiniciar el reloj.
- [ ] **S04-CA-04** (S04-RF-04) — Dada conversación o procesamiento pendiente, Cuando se cancele o expire el lease tras recarga, Entonces no se publica informe, el audio temporal no es accesible y el cupo se libera tras cancelar las tareas activas.
- [ ] **S04-CA-05** (S04-RF-05) — Dado un fallo ASR o de informe, Cuando el estudiante pulse reintentar una vez, Entonces se recupera la operación sin duplicar efectos; si falla de nuevo o vence la ventana, la práctica queda incompleta y ofrece comenzar otra.
- [ ] **S04-CA-06** (S04-RF-06) — Dadas cinco frases válidas e informe validado, Cuando termine limpieza, Entonces informe y completed aparecen juntos; si se cancela o borra antes del commit, el resultado tardío no los recrea.
- [ ] **S04-CA-07** (S04-RF-07) — Dado un comando start/retry y una versión vieja, Cuando se repita con misma clave o versión incompatible, Entonces se obtiene el recurso original o STATE_CONFLICT y no cambia el reloj ni el número de reintentos.

## 7. Diseño técnico y datos

**Datos:** `Practice`, lease de cupo, versiones, reloj y registro durable de operaciones. Solo este módulo cambia el estado global; Frases y Evaluador entregan resultados y no marcan la práctica completa.

**Backend:** rutas `/practices`, start/cancel/retry y GET, C-03. Transición atómica con estado, versión y cupo; `POST /start` requiere readiness del canal y preflight del navegador, que no sustituye permisos de servidor. Un catálogo o consentimiento cambiado produce conflicto antes de capturar.

**Eventos:** C-04 `practice.state_changed` y `practice.error`; deduplicación por ID/versiones. Finalización de voz cancela la generación y descarta audio tardío antes de mostrar frases. Ventanas y deadlines en C-07.

**Frontend:** B representa estados y temporizador aproximado sincronizado con servidor. Copias: «El servidor está ocupado. Intenta de nuevo.», «La sesión quedó incompleta. Puedes iniciar otra.», «Ocurrió un problema. Puedes reintentar una vez.» No promete reanudar tras recarga.

**Proxy/local:** mismo API/canal, sin servicio de reloj ni puerto extra.

**Tecnologías/ADR:** transacción o mecanismo equivalente de exclusión durable; ADR-003 fija lease, recuperación tras reinicio y cuándo liberar GPU. Reservar cupo durante processing evita solapamientos hasta medir otra política.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| Orquestador → SPEC-03/02/06 | Crear práctica válida | ActorContext, snapshot y ConsentRecord | 401/404/409 antes de reservar o grabar. |
| SPEC-05/07/08 → Orquestador | Notificar progreso y fallos | C-04/C-05, IDs y state_version | Evento duplicado o tardío se ignora con registro técnico. |
| Orquestador ↔ SPEC-09/06/11 | Finalizar o cancelar sin resurrección | Ack de limpieza, validación de informe y deletion_epoch | No publicar si falta ack o el objetivo está revocado. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S04-D-01** — Máquina de estados, bloqueo conservador y tokens propuestos el 2026-10-29; el catálogo confirma una sola sesión, cancelación y reintento manual.

### Preguntas abiertas

- **S04-P-01 — parcialmente resuelta el 2026-10-30:** el cupo se conserva desde `ready` hasta `processing` (opción larga) y el MVP atiende un solo usuario a la vez. Falta acordar la transición al vencimiento; A con B/C, antes de G1, porque la máquina compartida se implementa en las semanas 2 y 3.
- **S04-P-02 — bloqueante G1 solo para deadlines de operación:** fijarlos antes de integrar audio real. Lease, heartbeat y ventana de recuperación se fijan en ADR-003 durante la iteración 2 (D-17); A/B/C.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S04-RF-01 → S04-CA-01 | Concurrencia/contrato; reserva única y respuestas. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S04-RF-02 → S04-CA-02 | Integración/UI; consulta disponible bajo cupo. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S04-RF-03 → S04-CA-03 | Unidad/contrato; fronteras 299999/300000 y 599999/600000 ms. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S04-RF-04 → S04-CA-04 | Integración; cancelación, recarga y limpieza. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S04-RF-05 → S04-CA-05 | Integración/UI; éxito y agotamiento de recuperación. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S04-RF-06 → S04-CA-06 | Carreras/contrato; commit y epoch de borrado. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| S04-RF-07 → S04-CA-07 | Unidad/integración; máquina de estados y claves. | Escenario CA-07 satisfecho y evidencia adjunta al cierre. |
| RF-01, RF-13 | Validación y reloj con control de tiempo | Opciones y transiciones correctas. |
| RF-18 | Inyección de fallo por etapa, recarga, reinicio y reintento | Estados terminales y motivos verificables. |
| RNF-01 | Emitir tiempos de transición y correlación | Trazas para SPEC-01/12, sin umbral inventado. |
| RNF-09 | Comandos anónimos y de otra cuenta | 401/404 sin efectos. |
| RNF-10 | Inicios simultáneos e historial bajo ocupación | Una reserva; consultas continúan. |
| RNF-12 | Estados y acciones en español | Inspección UI con teclado. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** L: estados, concurrencia, recuperación y coordinación de limpieza/publicación.
- **Riesgos:** Cupo huérfano tras caída, temporizadores de cliente, duplicados y carreras de cancelación; integrar primero con fixtures.
- **Consecuencias:** Sin reanudación durable de voz; estados terminales se mantienen legibles en historial hasta borrarlos.
