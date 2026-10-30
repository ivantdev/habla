# SPEC-09 — Informe sustentado de pronunciación, gramática y vocabulario

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Informe  
> **RF relacionados:** RF-08, RF-14 | **RNF:** RNF-04, RNF-05, RNF-06, RNF-12  
> **RT:** RT-05, RT-06  
> **Módulo:** Informe | **Responsable:** C; B implementa la vista de informe  
> **Etapa:** E2–E3 | **Iteración:** 1: anclas y citas; 2: recortes de conversación, sus referencias, RT-05 y RT-06 | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

El valor del producto es un informe posterior a la práctica que señale observaciones reales, sin atribuir al estudiante ejemplos inventados ni convertir la incertidumbre en una nota.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existe agregador, análisis lingüístico, validador de citas ni publicación. Esta spec implementa también extracción/análisis de gramática y vocabulario; no se deja implícito como servicio externo ya disponible.

## 3. Historia de usuario

> Como estudiante, quiero entender qué puedo mejorar y escuchar la evidencia para que las recomendaciones correspondan a lo que realmente dije.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro del alcance de la spec

- Agregación acústica, análisis de gramática/vocabulario y redacción en español.
- Validación estructural y de citas, referencias, recortes y reproducción.
- Construcción privada, limpieza y publicación mediante orquestador; vista de informe.

### Fuera del alcance de la spec

- Nota global, certificación, informe de sesión incompleta o eficacia pedagógica demostrada.
- Corregir al estudiante durante conversación o inferir pronunciación solo del texto.

### Supuestos acordados

- Confirmados: cinco anclas válidas, tres categorías, evidencia y ausencia explícita de observaciones respaldadas. El formato C-06 es diseño propuesto hasta G0.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S09-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S09-RF-01** (RF-08) — CUANDO termine el procesamiento de una práctica con cinco anclas válidas y conversación cerrada, EL SISTEMA DEBE construir un borrador privado con las tres categorías y limitaciones en español.
- **S09-RF-02** (RF-08, RF-14, RNF-04, RNF-05) — CUANDO se proponga una observación de pronunciación, EL SISTEMA DEBE vincularla con evidencia acústica existente, intervalo y audio/referencia correspondientes, excluyendo unidades dudosas.
- **S09-RF-03** (RF-08, RNF-04) — CUANDO se proponga una observación de gramática o vocabulario, EL SISTEMA DEBE referirla a un turno final del estudiante y comprobar que la cita atribuida existe en su transcripción.
- **S09-RF-04** (RF-08, RNF-05) — SI una categoría no tiene observaciones respaldadas o no pudo evaluarse por falta de evidencia válida, ENTONCES EL SISTEMA DEBE distinguir esos estados sin inventar errores ni afirmar dominio perfecto.
- **S09-RF-05** (RF-08, RF-14) — CUANDO el borrador validado y los recortes/referencias estén preparados, EL SISTEMA DEBE solicitar limpieza de temporales y publicar únicamente mediante el commit autorizado del orquestador.
- **S09-RF-06** (RF-08; contrato con RF-18) — SI falla el procesamiento acústico, lingüístico o de referencias por una causa técnica, ENTONCES EL SISTEMA DEBE informar el fallo recuperable sin publicar un informe parcial como completo.
- **S09-RF-07** (RNF-06, RF-08) — EL SISTEMA DEBE presentar recomendaciones conforme a la guía pedagógica sin nota global, certificación ni afirmaciones de mejora no demostradas.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S09-CA-01** (S09-RF-01) — Dadas cinco válidas y tareas completadas, Cuando se construya el borrador, Entonces contiene pronunciación/gramática/vocabulario en español y no es accesible como informe público antes del commit.
- [ ] **S09-CA-02** (S09-RF-02) — Dadas evidencia válida, unidad dudosa y referencia inexistente, Cuando se valide el borrador, Entonces solo la observación sustentada puede publicarse y la cobertura excluida figura como limitación; el recorte de conversación debe estar preparado.
- [ ] **S09-CA-03** (S09-RF-03) — Dada una salida lingüística con cita real, otra inventada y una del tutor, Cuando se valide, Entonces solo la cita del estudiante existente sobrevive y las rechazadas quedan en diagnóstico privado sin atribuirse al usuario.
- [ ] **S09-CA-04** (S09-RF-04) — Dados resultados sin detecciones y otros sin oportunidades evaluadas, Cuando se renderice, Entonces muestra respectivamente «Sin observaciones respaldadas» y «No se pudo evaluar» con motivo y no una nota.
- [ ] **S09-CA-05** (S09-RF-05) — Dado borrador listo, Cuando falle limpieza o llegue cancelación/borrado antes de commit, Entonces no aparece informe; con ack y versión vigentes se publica una vez y los temporales desaparecen.
- [ ] **S09-CA-06** (S09-RF-06) — Dado un timeout de análisis lingüístico o generación de referencia, Cuando suceda, Entonces aparece reintento de operación por SPEC-04; si se agota, la práctica queda incompleta sin informe.
- [ ] **S09-CA-07** (S09-RF-07) — Dado un informe con observaciones de los tres tipos, Cuando se inspeccione vista y respuesta, Entonces hay explicación accionable acorde a la guía y no campos o textos de nota global/certificación.

## 7. Diseño técnico y datos

**Datos:** `Report`, `Observation` y referencias a evidencia/turnos de C-06. No copiar bytes de audio. El informe preserva las citas/IDs y el respaldo estructurado necesario tras borrar el temporal; borrar sesión o cuenta elimina ese contenido.

**Backend:** `Report.build` y GET de informe en C-03/C-05/C-06. La etapa lingüística recibe solo turnos finales del estudiante y contexto necesario; su salida estructurada pasa por validación de citas/hablante y revisión por corpus. Publicación exige cardinalidad, versiones, cobertura, referencias y estado válidos. Un filtro de citas elimina atribuciones inexistentes, pero no sustituye medir precisión lingüística en SPEC-01. La finalización usa los checkpoints de C-05: prepara evidencia y assets antes de borrar temporales y conserva el borrador para reintentar solo la etapa fallida. La visibilidad depende del commit del orquestador; no se exige atomicidad entre disco y base ni se escriben tablas privadas de otros módulos.

**Eventos:** `processing.updated` por etapa y `report.ready` solo tras commit. El trabajo conserva `operation_id` y epoch; reintentos no generan dos informes. No distribuir un evento final antes de confirmar transacción y limpieza.

**Frontend:** B implementa la vista de informe a partir del DTO de C, que la revisa, en el detalle de sesión: tres categorías, motivos de incertidumbre, observaciones y pares de reproductores. Tras audio vencido/borrado mantiene texto con estado de indisponibilidad; botones de reproducción no prometen acceso. Controles en español y navegación por teclado.

**Proxy/local:** GET autenticado de informe y audio por origen común, sin llamadas directas del navegador a proveedores.

**Tecnologías/ADR:** análisis lingüístico con modelo o reglas es decisión de C documentada en ADR-002; si se usa generador, exigir esquema y validación de evidencia. La referencia de recortes debe generarse con el TTS estadounidense aprobado y texto validado antes de publicación; es un asset privado ligado al recorte, no contenido del catálogo. Una cita sin respaldo se filtra; un fallo técnico al preparar audio que sí es necesario pasa a recuperación, no se disfraza de ausencia de observaciones.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| SPEC-04/07 → Informe | Acreditar fase y cinco válidas | Practice/AnchorAttempt y versiones | Falta de una muestra impide construir/publicar. |
| Informe → SPEC-05/08 | Obtener turnos y evidencia | C-05 con origen de cada cita | Duda se excluye; fallo técnico se recupera o termina incompleta. |
| Informe ↔ SPEC-06/04 | Recortes, limpieza y publicación | C-05/C-06, ack y epoch | Sin ack/permiso no publicación; resultado tardío se descarta. |
| SPEC-10/01 → Informe | Presentar y evaluar calidad | Report y corpus anotado | Sin informe publicado GET devuelve REPORT_NOT_READY. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S09-D-01** — RF-08/RNF-04 confirman evidencia y categorías; borrador privado y commit coordinado son diseño propuesto el 2026-10-29.

### Preguntas abiertas

- **S09-P-01 — bloqueante G1 para generador real:** Definir modelo/reglas lingüísticas, prompts versionados y esquema de salida; C con política de datos de A.
- **S09-P-02 — bloqueante G2 para el texto de explicaciones; iteración 2 para referencias de recortes:** acordar ambos; C/B antes del recorrido integrado correspondiente.
- **S09-P-03 — bloqueante G3:** Muestra humana y criterio de calidad lingüística; C/B mediante SPEC-01 antes de aceptación. Nicolás (B) realiza las anotaciones humanas según la [especificación de métricas](../experiments/METRICS.md).

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S09-RF-01 → S09-CA-01 | Contrato/integración; esquema y visibilidad. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S09-RF-02 → S09-CA-02 | Contrato/integración; validación de refs y reproductores. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S09-RF-03 → S09-CA-03 | Unidad/contrato; citas, hablante e ID de turno. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S09-RF-04 → S09-CA-04 | UI/contrato; categorías vacías y no evaluadas. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S09-RF-05 → S09-CA-05 | Integración/carreras; limpieza y publicación atómica. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S09-RF-06 → S09-CA-06 | Fallo/integración; diferencias entre falta de evidencia y error técnico. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| S09-RF-07 → S09-CA-07 | Revisión/UI; texto e integridad del esquema. | Escenario CA-07 satisfecho y evidencia adjunta al cierre. |
| RF-08 | Menos/cinco anclas, categorías y terminales | Solo informe completo y sustentado. |
| RF-14 | Recortes, marcas y referencias | Correspondencia acústica y estado de reproducción. |
| RNF-04, RNF-05 | Citas inventadas, tutor, evidencia inexistente y duda | Sin atribuciones no respaldadas; limitaciones explícitas. |
| RNF-06 | Revisión de recomendaciones con guía | No penalizar variación comprensible. |
| RNF-12 | Informe en español, foco y reproductores | Recorrido UI por teclado. |
| RT-05, RT-06 | Exportar variantes para SPEC-01 sin contaminar prueba | Resultados evaluables con anotaciones, no métricas inventadas. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** L: agregación, análisis lingüístico, validación, recortes y publicación; reutilizar contratos y UI común.
- **Riesgos:** Alucinaciones con citas parecidas pero falsas, audio recortado sin referencia y confundir categoría vacía con fallo técnico.
- **Consecuencias:** Ausencia de observaciones no acredita perfección. La calidad lingüística se mide separada de la validez estructural.
