# SPEC-11 — Eliminación de audio, sesiones y cuenta

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Ciclo de vida y privacidad  
> **RF relacionados:** RF-16, RF-20 | **RNF:** RNF-07, RNF-09, RNF-12  
> **RT:** No aplica directamente  
> **Módulo:** Ciclo de vida y privacidad | **Responsable:** B; A provee revocación de audio e identidad y C cancela trabajos  
> **Etapa:** E3 | **Iteración:** 2 (P1, si alcanza para el pitch) | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

El propietario puede eliminar datos antes de su caducidad. Un borrado debe ser efectivo aunque haya modelos trabajando, respuestas cacheadas o una caída entre revocación y limpieza física.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existe coordinador de eliminación, tareas idempotentes ni acciones UI. SPEC-06 administra bytes y expiración; aquí se coordina la eliminación de todas las entidades que correspondan.

## 3. Historia de usuario

> Como estudiante, quiero borrar un audio, una práctica o mi cuenta para dejar de tener esos datos almacenados y disponibles.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Solicitud propia, confirmación de acción y revocación inmediata.
- Cascada de datos, cancelación de trabajos, limpieza física recuperable y estados de operación.
- Protección contra resultados tardíos, doble borrado y caídas.

### Fuera de esta iteración

- Recuperar datos borrados, exportación masiva, panel administrativo o nueva política de conservación.
- Mantener textos/informes de una sesión o cuenta ya eliminada.

### Supuestos acordados

- Confirmados: borrar audio conserva informe, borrar sesión/cuenta elimina datos asociados. La operación durable con revocación antes de responder es diseño propuesto.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S11-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S11-RF-01** (RF-16, RF-20) — CUANDO el propietario solicite eliminar un audio, EL SISTEMA DEBE revocar su reproducción antes de confirmar la solicitud y coordinar la eliminación de sus bytes sin borrar el texto del informe.
- **S11-RF-02** (RF-16, RNF-07) — CUANDO el propietario solicite eliminar una sesión, EL SISTEMA DEBE ocultarla de consultas, cancelar sus trabajos y eliminar audio, transcripción, evidencias e informe asociados.
- **S11-RF-03** (RF-16, RNF-09) — CUANDO el propietario solicite eliminar su cuenta, EL SISTEMA DEBE revocar todas sus sesiones autenticadas y coordinar la eliminación de la cuenta y todos sus datos de práctica.
- **S11-RF-04** (RNF-07) — SI una eliminación física falla o el servicio se reinicia, ENTONCES EL SISTEMA DEBE conservar la revocación y reanudar idempotentemente las tareas pendientes sin restaurar datos ni declarar finalización falsa.
- **S11-RF-05** (RNF-09) — SI otra cuenta o una petición anónima intenta borrar un recurso, ENTONCES EL SISTEMA DEBE rechazar la solicitud sin modificar datos ni revelar su existencia.
- **S11-RF-06** (RF-16, RNF-07) — MIENTRAS exista una eliminación en curso, EL SISTEMA DEBE impedir que trabajos con un token anterior vuelvan a publicar o conservar datos del objetivo eliminado.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S11-CA-01** (S11-RF-01) — Dado audio propio mencionado en informe y una referencia privada generada desde su fragmento, Cuando se borre y se usen enlaces anteriores, Entonces no se reciben bytes de ninguno y el informe mantiene su texto con audio eliminado.
- [ ] **S11-CA-02** (S11-RF-02) — Dada práctica activa o completada, Cuando se elimine, Entonces deja de aparecer inmediatamente y al concluir la operación no quedan sus datos ni resultados tardíos aceptados.
- [ ] **S11-CA-03** (S11-RF-03) — Dada cuenta con dos sesiones web, prácticas, consentimientos y trabajos, Cuando confirme borrado, Entonces ambas cookies y canales quedan revocados, la UI sale y el inventario posterior no contiene su correo, credenciales, consentimientos personales, textos o audio.
- [ ] **S11-CA-04** (S11-RF-04) — Dado fallo de disco entre revocación y borrado, Cuando reinicie y se repita la tarea, Entonces los datos siguen inaccesibles y la operación solo pasa a succeeded tras los acknowledgments de los módulos.
- [ ] **S11-CA-05** (S11-RF-05) — Dado recurso de A, Cuando B o anónimo solicite cada DELETE, Entonces obtiene 404/401 y los datos de A continúan; repetir borrado propio no recrea ni duplica tareas.
- [ ] **S11-CA-06** (S11-RF-06) — Dado informe/evaluación/recorte pendiente con epoch viejo, Cuando llegue después de borrar, Entonces su resultado se descarta, el temporal se limpia y no se recrean proyecciones, evidencias ni referencias reproducibles.

## 7. Diseño técnico y datos

**Datos:** `DeletionOperation` con target, epoch y acknowledgments por módulo. Un tombstone técnico mínimo puede permanecer mientras se resuelve la limpieza; no incluye correo, transcripción, audio ni informe. ADR-003 fija plazo de depuración de registros técnicos y qué evidencia operacional no personal se conserva.

**Backend:** DELETE de C-03 y `Deletion.request` en C-05. Primero validar actor, establecer barrera/epoch y revocar acceso; después despachar tareas privadas de limpieza. Orden para cuenta: bloquear identidad y canales, cancelar práctica/liberar recursos, pedir eliminación a cada propietario de datos y eliminar identidad personal al completar. El inventario incluye consentimientos personales, sesiones web, referencias privadas de recortes, cachés/proyecciones y registros de idempotencia que contengan datos personales; los mínimos técnicos pendientes se depuran según ADR-003. No esperar a que el usuario siga autenticado para continuar limpieza.

**Eventos:** mensajes internos idempotentes por operación/target/version. Proyecciones descartan eventos anteriores al tombstone. El borrado de cuenta invalida GET de operación autenticado; la interfaz confirma solicitud y salida, mientras la evidencia final es operativa.

**Frontend:** acciones de audio, sesión y cuenta con confirmación que explicita qué se elimina. Español, foco/restauración accesible, estado de solicitud y error. No mostrar «Todo eliminado» tras un mero 202 pendiente. Un borrado no vuelve a habilitarse por fallar la limpieza física.

**Proxy/local:** DELETE y GET de operación por API con identidad/CSRF; ninguna llamada directa al disco ni a proveedor desde navegador.

**Tecnologías/ADR:** tarea durable en almacenamiento acordado en G0, sin broker obligatorio. Integrar proveedores externos solo si hay política verificada de datos y eliminación; registrar restricciones reales antes de usarlos.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| Cliente/B → Eliminación | Solicitar acción y consultar estado | C-03, actor y target propio | 401/404 y mensajes sin datos ajenos. |
| Eliminación → SPEC-03/04/06 | Revocar, cancelar y borrar bytes | Funciones internas y acknowledgments de C-05 | Fallo físico mantiene inaccesibilidad y operación pendiente. |
| Eliminación → SPEC-05/07/08/09/10 | Eliminar datos privados y proyecciones | Operación/epoch por módulo | Cada propietario confirma su limpieza; resultados viejos se descartan. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S11-D-01** — RF-16/RNF-07 definen cascada; coordinación durable y barrera de borrado propuestas el 2026-10-29.

### Preguntas abiertas

- **S11-P-01 — bloqueante para integrar el borrado (iteración 2):** Fijar plazo de limpieza de bytes y registros técnicos, inventario de caches y políticas externas si aplican; B con A/C, ADR-003.
- **S11-P-02 — bloqueante para integrar el borrado (iteración 2):** Cada módulo declara su operación de cancelación/eliminación y acknowledgment; B con A/C antes de la prueba de carreras.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S11-RF-01 → S11-CA-01 | Integración/UI; revocación e inventario final. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S11-RF-02 → S11-CA-02 | Integración/carreras; cascada e inventario. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S11-RF-03 → S11-CA-03 | Integración; múltiples sesiones y limpieza por módulo. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S11-RF-04 → S11-CA-04 | Inyección de fallo/reinicio; operación durable. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S11-RF-05 → S11-CA-05 | Contrato; permisos y repetición. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S11-RF-06 → S11-CA-06 | Concurrencia; barreras y versiones. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| RF-16 | Borrado de audio, sesión y cuenta en cada estado | Inventario antes/después y acceso revocado. |
| RF-20 | Audio eliminado con informe conservado | Texto visible, reproducción bloqueada. |
| RNF-07 | Fallo físico, reinicio, recortes y caches | Limpieza dentro del plazo declarado; pendientes visibles. |
| RNF-09 | Matriz de DELETE y todas las cookies revocadas | Sin borrado ajeno ni acceso con cookie vieja. |
| RNF-12 | Confirmaciones y estados por teclado | Efecto explicado y 202 sin promesa de limpieza final. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** L: coordinación transversal y recuperación; no posponer la barrera de revocación hasta el final del proyecto.
- **Riesgos:** Resurrección por worker/proyección, archivos huérfanos y registros técnicos con datos personales.
- **Consecuencias:** La disponibilidad se revoca inmediatamente; la limpieza física puede requerir reintentos operativos verificables.
