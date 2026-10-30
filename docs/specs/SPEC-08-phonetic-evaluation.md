# SPEC-08 — Evaluación acústica, validez y evidencia fonética

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Evaluación fonética  
> **RF relacionados:** RF-06 | **RNF:** RNF-02, RNF-04, RNF-05, RNF-06, RNF-11, RNF-14  
> **RT:** RT-02  
> **Módulo:** Evaluación fonética | **Responsable:** C; A revisa aislamiento y B consume validez  
> **Etapa:** E1–E3 | **Iteración:** 1: anclas; 2: conversación libre y evaluación final | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

La pronunciación debe analizarse con audio, independientemente de la transcripción conversacional. La evidencia y cobertura deben ser suficientes para explicar observaciones y comparar sonidos sin interpretar ausencia de evidencia como acierto.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No hay adaptador, validador ni esquema de evidencia ejecutable. SPEC-01 decide políticas y motor a partir de experimentos; aquí se implementa su integración en la sesión.

## 3. Historia de usuario

> Como estudiante, quiero observaciones basadas en mi voz y límites de evaluación explícitos para no recibir errores inferidos únicamente del texto.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Adaptador de audio a evidencia normalizada y validador de anclas.
- Cobertura por unidad/sonido, exclusión por incertidumbre, versiones y deduplicación.
- Tarea desacoplada de conversación con cancelación, deadline y cola acotada.

### Fuera de esta iteración

- Fijar métricas con prueba, elegir el modelo sin SPEC-01 o emitir nota global.
- Validar muestra por parecido exacto al acento de referencia.

### Supuestos acordados

- Confirmados: ruta acústica independiente, excluir conversación dudosa y texto conocido para anclas. Los campos de C-05 son contrato propuesto; las escalas de confianza se calibran, no se presuponen.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S08-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S08-RF-01** (RF-06, RNF-04) — CUANDO se solicite evaluación fonética, EL SISTEMA DEBE obtener el audio autorizado y generar evidencia acústica normalizada con intervalos, método y versión del evaluador.
- **S08-RF-02** (RNF-05) — SI una palabra de conversación tiene transcripción dudosa según la política calibrada, ENTONCES EL SISTEMA DEBE excluirla de detección fonética y registrar cobertura no evaluada con su motivo sin pedir repetición.
- **S08-RF-03** (RNF-14) — CUANDO se valide una frase ancla, EL SISTEMA DEBE distinguir voz utilizable, cobertura del texto y evaluabilidad de los errores de pronunciación observados.
- **S08-RF-04** (RNF-11) — CUANDO se complete un análisis, EL SISTEMA DEBE conservar tanto oportunidades evaluadas como unidades no evaluadas y errores detectados con versiones compatibles para comparación.
- **S08-RF-05** (RNF-02) — MIENTRAS se ejecute análisis fonético, EL SISTEMA DEBE procesarlo fuera del ciclo que atiende la conversación y dentro de los límites de cola y recursos acordados.
- **S08-RF-06** (RNF-04; contrato con RF-18) — SI un trabajo está duplicado, cancelado, vencido o pertenece a datos revocados, ENTONCES EL SISTEMA DEBE evitar efectos repetidos o publicación de evidencia inválida y comunicar su resultado al orquestador.
- **S08-RF-07** (RNF-06) — CUANDO una diferencia fonética se proponga como error, EL SISTEMA DEBE aplicar la guía pedagógica y conservar la evidencia y el umbral que sustentan esa decisión.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S08-CA-01** (S08-RF-01) — Dados audio y transcripción igual para dos pronunciaciones distintas, Cuando se evalúen, Entonces el adaptador puede producir resultados distintos basados en señal y cada evidencia refiere al asset e intervalo reales.
- [ ] **S08-CA-02** (S08-RF-02) — Dados tokens con confianza a ambos lados del umbral y otro sin indicador disponible, Cuando se evalúen, Entonces los dudosos/no sustentados quedan no evaluados y no cuentan como correctos ni errores.
- [ ] **S08-CA-03** (S08-RF-03) — Dadas muestras silenciosa, truncada, de texto distinto y evaluable con error, Cuando se valide, Entonces las tres primeras llevan motivo calibrado y la última es válida.
- [ ] **S08-CA-04** (S08-RF-04) — Dado análisis con dos errores, oportunidades sin error y unidades dudosas, Cuando se exporte, Entonces los denominadores conservan las oportunidades y las dudosas aparecen separadas; nunca se deduce acierto de una lista vacía.
- [ ] **S08-CA-05** (S08-RF-05) — Dado análisis lento en GPU y un nuevo turno, Cuando opere el sistema, Entonces los controles/conversación responden y la cola no crece sin límite ni pierde unidades sin registrar cobertura.
- [ ] **S08-CA-06** (S08-RF-06) — Dado job duplicado y otro que termina después de borrar, Cuando regresen sus resultados, Entonces solo el primero autorizado se almacena una vez y el revocado no recrea datos; un timeout solicita recuperación.
- [ ] **S08-CA-07** (S08-RF-07) — Dadas diferencias de acento comprensibles y errores que afectan comprensión de la guía, Cuando se filtre evidencia, Entonces se respeta su clasificación y se registra versión/motivo de decisión.

## 7. Diseño técnico y datos

**Datos:** resultados, cobertura y evidencia de C-05; no almacenar copias de audio fuera de Audio. La confianza de ASR y la confianza del detector son campos distintos y no se intercambian. Anclas usan texto conocido del snapshot; conversación usa tokens y política de incertidumbre.

**Backend:** `Evaluator.validateAnchor` y `Evaluator.analyze` internos, con trabajo y refs de C-05. No endpoint público que permita evaluar una ruta/asset ajeno. El adaptador traduce salida de proveedor sin inventar fonemas si solo hay puntuación agregada; tal proveedor no satisface por sí solo esta interfaz.

**Eventos/tareas:** deduplicación por job/versión, deadline y cancelación por epoch. Estado global es de SPEC-04. Si la cola se satura, comunicar fallo operativo recuperable; no publicar éxito con unidades silenciosamente perdidas.

**Frontend:** ninguna pantalla nueva; SPEC-07 consume validez y SPEC-09 cobertura/limitaciones. No mostrar juicios en conversación.

**Proxy/local:** inferencia interna sin entrada pública; configurar límite de memoria/concurrencia y autorización entre procesos en ADR-001/003.

**Tecnologías/ADR:** implementar el motor preliminar de ADR-002 detrás de esta interfaz; aislar capacidades para poder sustituirlo tras la comparación. Las tecnologías candidatas del catálogo no constituyen una elección.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| SPEC-05/07 → Evaluador | Analizar audio/validar ancla | C-05 con audio_id y texto/confianza | Sin audio autorizado no existe análisis válido. |
| Evaluador → SPEC-06/01 | Leer bytes y política versionada | Audio.readForJob y calibración | INPUT_REVOKED/versión ausente impide procesar. |
| SPEC-09/10 → Evaluador | Consumir respaldo y denominadores | PhoneticResult, IDs y versiones | Cobertura vacía se declara no evaluada; incompatibilidad se conserva. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S08-D-01** — Ruta independiente y exclusión de duda son catálogo; interfaz normalizada propuesta el 2026-10-29.

### Preguntas abiertas

- **S08-P-01 — bloqueante G1 para adaptador real:** Motor preliminar, granularidad y política de confianza/validez; C en SPEC-01 antes de conectar audio real.
- **S08-P-02 — bloqueante G3:** Congelar evaluador/calibración y criterios pedagógicos antes de prueba final; C/B con ADR-002.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S08-RF-01 → S08-CA-01 | Integración acústica; entrada real y evidencia verificable. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S08-RF-02 → S08-CA-02 | Unidad/contrato; fronteras y ausencia de indicador. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S08-RF-03 → S08-CA-03 | Evaluación/integración; conjunto etiquetado de validez. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S08-RF-04 → S08-CA-04 | Contrato; PhoneticResult y conteos trazables. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S08-RF-05 → S08-CA-05 | Rendimiento/integración; cola, recursos y latencia. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S08-RF-06 → S08-CA-06 | Fallo/concurrencia; deduplicación y epoch. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| S08-RF-07 → S08-CA-07 | Evaluación/revisión; resultados contra etiquetas. | Escenario CA-07 satisfecho y evidencia adjunta al cierre. |
| RF-06, RNF-04 | Variar audio manteniendo texto; inspeccionar evidencia | Decisión derivada de señal y refs válidas. |
| RNF-02 | Evaluador lento y cola saturada | No bloqueo conversacional ni pérdida silenciosa. |
| RNF-05, RNF-14 | Confianza, silencio, truncado y texto conocido | Cobertura/validez con motivos y límites. |
| RNF-06 | Casos anotados con variación de acento | Filtrado acorde a guía. |
| RNF-11 | Versiones y denominadores por sonido | Conteos verificables de oportunidades. |
| RT-02 | Cambiar adaptador manteniendo contrato | Pruebas compartidas de capacidades; selección en SPEC-01. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** L: adaptación acústica, cobertura, validez, cancelación y recursos.
- **Riesgos:** Salida externa insuficiente, alineación dudosa y confundir la confianza de ASR con la del detector.
- **Consecuencias:** Las unidades excluidas se muestran como límite; la elección de motor queda detrás de un contrato estable.
