# SPEC-02 — Catálogo pedagógico, frases y referencias

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Contenido  
> **RF relacionados:** RF-01, RF-07, RF-09 | **RNF:** RNF-06, RNF-08, RNF-11, RNF-12  
> **RT:** No aplica directamente  
> **Módulo:** Contenido | **Responsable:** B; revisión acústica de C  
> **Etapa:** E0–E1 | **Versión:** 1.0 | **Actualizado:** 2026-10-29

## 1. Contexto y problema

La práctica requiere contenido consistente entre sesiones. Las cinco frases fijas y sus referencias permiten comparar por sonido; los temas necesitan objetivos adecuados a cada nivel, sin confundir diferencias de acento con errores.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

Los nombres de niveles y temas están definidos, pero no existen fichas, textos de frases, referencias habladas ni política detallada del tutor. No existe frontend al que atribuir estos contenidos.

## 3. Historia de usuario

> Como estudiante, quiero elegir una práctica apropiada para mi nivel y escuchar referencias consistentes para entender la actividad y comparar mi pronunciación.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Tres niveles, cinco temas y objetivos de vocabulario/estructuras para las quince combinaciones.
- Cinco frases en inglés con IDs, orden, sonidos objetivo y referencia estadounidense.
- Guía pedagógica, política del tutor y versión de catálogo congelada por práctica.

### Fuera de esta iteración

- Nuevos idiomas, frases aleatorias por sesión y certificación del nivel.
- Administración de contenido mediante una pantalla nueva.

### Supuestos acordados

- Confirmados: niveles, temas, cinco frases iguales y referencia estadounidense. Los textos y las reglas de redirección temática son entregables por preparar, no acuerdos previos.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S02-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S02-RF-01** (RF-01) — CUANDO se consulte el catálogo, EL SISTEMA DEBE ofrecer exactamente los niveles A2, B1 y B2 y los cinco temas definidos con objetivos para cada combinación.
- **S02-RF-02** (RF-07, RF-09) — EL SISTEMA DEBE identificar un conjunto versionado de exactamente cinco frases en inglés con orden estable, sonidos objetivo y referencia hablada estadounidense.
- **S02-RF-03** (RNF-11) — CUANDO se cree una práctica, EL SISTEMA DEBE conservar las versiones de contenido usadas aunque se publique posteriormente otro catálogo.
- **S02-RF-04** (RF-01, RNF-08) — CUANDO se entregue la política del tutor al módulo conversacional, EL SISTEMA DEBE incluir nivel, objetivos temáticos, reserva de correcciones y comportamiento acordado ante solicitudes fuera del contexto permitido.
- **S02-RF-05** (RNF-06) — CUANDO se revise la guía de errores, EL SISTEMA DEBE distinguir los errores que dificultan comprensión de diferencias de acento comprensibles y vincular los sonidos objetivo con la guía.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S02-CA-01** (S02-RF-01) — Dado el catálogo aprobado, Cuando se consulte cada tema y nivel, Entonces existen quince fichas completas y no aparecen idiomas o niveles adicionales.
- [ ] **S02-CA-02** (S02-RF-02) — Dado el conjunto publicado, Cuando se inspeccionen sus cinco entradas, Entonces cada una tiene ID único, texto y referencia reproducible correspondiente al mismo texto.
- [ ] **S02-CA-03** (S02-RF-03) — Dada una práctica con versión V1 y un catálogo V2 posterior, Cuando se consulten sus frases, Entonces sigue utilizando V1 y su clave de comparación no cambia.
- [ ] **S02-CA-04** (S02-RF-04) — Dada una ficha y la política aprobada, Cuando se construya el contexto del tutor, Entonces contiene esos campos y los casos de salida de tema tienen una respuesta esperada revisada.
- [ ] **S02-CA-05** (S02-RF-05) — Dadas muestras de ambas clases, Cuando B y C apliquen la guía, Entonces quedan etiquetas y motivos explícitos y las diferencias comprensibles no se registran automáticamente como error.

## 7. Diseño técnico y datos

**Datos:** Contenido posee `Catalog`, `Topic`, `AnchorSet`, `AnchorPhrase` y política del tutor; referencias de audio son assets de contenido, sin caducidad de datos personales. Usar un manifiesto versionado es suficiente para el MVP.

**Backend:** `GET /catalog`, `GET /references/:id` y `Content.snapshot` de C-02/C-03/C-05. No hay mutación pública de contenido. El backend rechaza combinaciones ajenas al catálogo desde SPEC-04.

**Frontend:** B muestra selección y preparación; las frases y reproductores se integran en SPEC-07. Etiquetas españolas, frases inglesas y referencias con control por teclado.

**Eventos:** no canal propio; la práctica fija las versiones al crearse.

**Proxy/local:** `/api/v1/catalog` y referencias pasan por el proxy compartido; no servicio ni puerto nuevos.

**Tecnologías/ADR:** manifiesto estático o registros sembrados son alternativas; ADR-004 fija textos, procedencia/licencia de referencias, revisión del acento y política. Generar TTS estadounidense es una propuesta que requiere escucha, no una referencia automáticamente correcta.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| SPEC-04/05 → Contenido | Configurar práctica y tutor | C-02, Content.snapshot; consulta autenticada según contexto | Versión inexistente: rechazar configuración, no sustituir silenciosamente. |
| SPEC-07/08/10 → Contenido | Vincular texto, sonidos y comparabilidad | AnchorPhrase y anchor_set_version | Referencia ausente bloquea publicar el catálogo. |
| B ↔ C/SPEC-01 | Revisar cobertura y error pedagógico | Manifiesto y guía de anotación | Cobertura insuficiente obliga a revisar antes de G1. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S02-D-01** — Las categorías proceden de RF-01/RF-07; se propone catálogo inmutable por práctica el 2026-10-29.

### Preguntas abiertas

- **S02-P-01 — bloqueante G1:** Cerrar las cinco frases, referencias con licencia y quince fichas; B con C, antes de pruebas reales de frases.
- **S02-P-02 — bloqueante aceptación del tutor:** Precisar límites temáticos con la fuente de propuesta y casos esperados; B, antes de G2. La fuente externa no pudo verificarse al redactar estas specs; no se inventan restricciones adicionales.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S02-RF-01 → S02-CA-01 | Contrato/inspección; catálogo y fichas. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S02-RF-02 → S02-CA-02 | Contenido/contrato; manifiesto y escucha revisada. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S02-RF-03 → S02-CA-03 | Integración; snapshot/versiones. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S02-RF-04 → S02-CA-04 | Contrato/revisión; contexto y corpus del tutor. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S02-RF-05 → S02-CA-05 | Revisión pedagógica; ejemplos anotados. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| RF-01, RF-07, RF-09 | Integridad del catálogo y reproducción | Quince fichas, cinco frases y referencias verificadas. |
| RNF-06, RNF-08 | Revisión de guía y corpus de tutor | Casos anotados y política aprobada. |
| RNF-11 | Actualizar catálogo sin cambiar prácticas previas | Snapshots/versiones estables. |
| RNF-12 | Inspección de etiquetas y controles | Español de interfaz, inglés de práctica. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** M: contenido, referencias, contrato y revisión conjunta.
- **Riesgos:** Frases con cobertura pobre, licencia de referencia incierta o objetivos vagos retrasan validación acústica.
- **Consecuencias:** Cambiar frases implica nueva versión e incompatibilidad salvo equivalencia documentada; no se reescribe el pasado.
