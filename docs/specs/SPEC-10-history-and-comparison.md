# SPEC-10 — Historial propio y comparación por sonido

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Consulta y experiencia  
> **RF relacionados:** RF-09, RF-12, RF-20 | **RNF:** RNF-09, RNF-11, RNF-12  
> **RT:** No aplica directamente  
> **Módulo:** Consulta y experiencia | **Responsable:** A; B mantiene shell/router y C provee el informe  
> **Etapa:** E3 | **Versión:** 1.0 | **Actualizado:** 2026-10-29

## 1. Contexto y problema

El estudiante necesita recuperar sus informes y comparar sesiones sobre las mismas frases. Los audios caducan antes que el texto y las versiones de evaluación pueden volver injusta una comparación.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existen historial, detalle, proyección ni comparación. Este módulo consulta las fuentes de estado, informe, audio y cobertura, sin convertirse en escritor de sus datos.

## 3. Historia de usuario

> Como estudiante, quiero revisar mi historial y comparar sonidos entre sesiones compatibles para observar diferencias con evidencia y denominadores claros.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Listado paginado propio, detalle de estados e informe publicado.
- Reproductores y disponibilidad actual del audio; acceso a acciones de borrado de SPEC-11.
- Comparación de dos sesiones completadas propias y compatibles por sonido de anclas.

### Fuera de esta iteración

- Ranking, nota global, mapa de vocales, comparar conversación libre o afirmar aprendizaje por variación de resultados.
- Recalcular versiones antiguas o definir equivalencias no evaluadas entre motores.

### Supuestos acordados

- Confirmados: fecha, tema, nivel, estado, informe, audio vigente y comparación por sonido. Hasta ADR de equivalencia, solo versiones idénticas son compatibles.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S10-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S10-RF-01** (RF-12) — CUANDO un propietario consulte su historial, EL SISTEMA DEBE listar únicamente sus sesiones no borradas con fecha, tema, nivel, estado y disponibilidad de informe/audio en orden paginado estable.
- **S10-RF-02** (RF-09, RF-12) — CUANDO el propietario abra una sesión, EL SISTEMA DEBE mostrar su estado real y el informe solo si está publicado, incluyendo audios vigentes y sus referencias.
- **S10-RF-03** (RF-20) — SI un audio referenciado vence o se elimina después de cargar el historial, ENTONCES EL SISTEMA DEBE dejar de ofrecer su reproducción al recibir el estado vigente y conservar el texto del informe.
- **S10-RF-04** (RF-12, RNF-11) — CUANDO se seleccionen dos sesiones completadas propias y con versiones compatibles, EL SISTEMA DEBE comparar por sonido sus oportunidades evaluadas y errores de las mismas cinco frases, separando unidades no evaluadas.
- **S10-RF-05** (RNF-09, RNF-11) — SI las sesiones no son propias, están incompletas o usan versiones incompatibles, ENTONCES EL SISTEMA DEBE impedir la comparación y explicar el motivo permitido sin revelar datos ajenos.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S10-CA-01** (S10-RF-01) — Dadas sesiones de dos cuentas y dos páginas, Cuando A consulte historial incluyendo cursor, Entonces recibe solo las suyas en orden, sin duplicados ni sesiones borradas y sin exponer textos de B.
- [ ] **S10-CA-02** (S10-RF-02) — Dadas sesiones completada e incompleta, Cuando se abra cada detalle, Entonces la primera presenta informe/reproductores autorizados y la segunda motivo/estado sin informe aparente.
- [ ] **S10-CA-03** (S10-RF-03) — Dada página abierta con audio disponible, Cuando una nueva lectura devuelva vencido/eliminado, Entonces el reproductor informa indisponibilidad, no reintenta indefinidamente y el texto continúa visible.
- [ ] **S10-CA-04** (S10-RF-04) — Dadas dos sesiones compatibles con denominadores distintos y alguna unidad dudosa, Cuando se comparen, Entonces cada sonido muestra valores y oportunidades de ambas, las dudas por separado y ninguna nota global.
- [ ] **S10-CA-05** (S10-RF-05) — Dadas pareja con cuenta ajena, sesión incompleta y evaluadores distintos, Cuando se solicite comparación, Entonces responde 404 o conflicto apropiado; no hay mezcla ni equivalencia silenciosa.

## 7. Diseño técnico y datos

**Datos:** proyección `PracticeSummary` y vista de comparación de C-06. Las fuentes autoritativas son Practice, Report, Audio y PhoneticResult. La proyección puede reconstruirse y no concede acceso basándose solo en información cacheada. No usa tablas privadas directamente; interfaces internas entregan DTO por propietario.

**Backend:** GET /history, /practices/:id, /report y /comparisons de C-03. Cursor opaco con orden estable; límites de C-01. La comparación emplea `anchor_summary` publicado y clave de compatibilidad; cero oportunidades se muestra «Sin evidencia evaluable», nunca cero errores equivalente a acierto.

**Frontend:** `/sesiones`, `/sesiones/:id`, `/comparar`; fecha local del navegador con instante UTC conservado, estados españoles, historial vacío, carga y error. Selección de dos sesiones por teclado y tabla por sonido con denominadores explícitos; sin visualización de nota global.

**Eventos:** actualización de proyección por IDs/versiones; al abrir detalle/reproducir se revalida fuente. Consumidores descartan eventos repetidos y posteriores al borrado.

**Proxy/local:** consultas y audio por API autenticada; no caches públicas ni links duraderos a bytes.

**Tecnologías/ADR:** consulta agregada o proyección persistida según stack de G0; empezar por consulta con DTO si el volumen de demo no justifica otra persistencia. La comparación no necesita servicio nuevo.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| Historial → SPEC-03/04 | Autorizar y obtener estado | ActorContext y PracticeSummary | 401/404; no mostrar recurso ajeno. |
| Historial → SPEC-09/06 | Obtener informe/audio vigente | Report y AudioAsset | Informe no listo o audio no disponible se representan explícitamente. |
| Historial → SPEC-08/02 | Comparar datos/versiones | C-06 y anchor_set_version | Versiones incompatibles bloquean comparación. |
| Cliente → SPEC-11 | Borrar desde vistas | DELETE y Operation | Revocación elimina la tarjeta/acción; fallo físico no restaura acceso. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S10-D-01** — La comparación y permanencia de texto son RF-12/RF-20; regla conservadora de versiones idénticas propuesta el 2026-10-29.

### Preguntas abiertas

- **S10-P-01 — no bloqueante:** Ajustar presentación por sonido tras disponer de cobertura real; B/C antes de G3.
- **S10-P-02 — no bloqueante para MVP:** Permitir equivalencias entre versiones distintas requeriría ADR y evidencia; no implementarlo por defecto.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S10-RF-01 → S10-CA-01 | Contrato/integración; paginación, permisos y concurrencia de lectura. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S10-RF-02 → S10-CA-02 | UI/integración; detalle por estado. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S10-RF-03 → S10-CA-03 | UI/reloj; enlace antiguo y respuesta 410/404. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S10-RF-04 → S10-CA-04 | Contrato/UI; conteos conocidos y ausencia de evidencia. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S10-RF-05 → S10-CA-05 | Contrato/integración; matriz de compatibilidad y permiso. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| RF-09, RF-12 | Historial vacío, páginas, detalle y reproducción | Datos propios y estados correctos. |
| RF-20 | Caducidad y borrado con página abierta | Texto permanece y bytes no accesibles. |
| RNF-09 | Otra cuenta y cursor manipulado | Sin filtración de sesiones/informe/audio. |
| RNF-11 | Comparación compatible/incompatible y sin oportunidades | Denominadores/limitaciones sin nota. |
| RNF-12 | Teclado, etiquetas y lectura de tabla | Interfaz española comprensible. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** M: consultas, detalle, tabla y estados; B reutiliza reproductores e informe de specs previas.
- **Riesgos:** Comparar resultados sin denominador, confiar en cache obsoleta o usar versión de frases actual en sesiones antiguas.
- **Consecuencias:** La comparación describe resultados observados; no prueba aprendizaje ni conserva audio vencido.
