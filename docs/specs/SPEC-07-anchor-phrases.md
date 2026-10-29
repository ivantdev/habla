# SPEC-07 — Lectura y validación de las cinco frases ancla

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Frases ancla  
> **RF relacionados:** RF-07, RF-17 | **RNF:** RNF-09, RNF-12, RNF-14  
> **RT:** No aplica directamente  
> **Módulo:** Frases ancla | **Responsable:** B; C entrega validador  
> **Etapa:** E2 | **Versión:** 1.0 | **Actualizado:** 2026-10-29

## 1. Contexto y problema

Las frases fijas aportan muestras comparables. Una pronunciación con errores puede ser evaluable; repetir solo por ese motivo sesgaría la evaluación y rompería el límite acordado de dos reintentos.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existe flujo de lectura, conteo de intentos ni validador. La spec implementa la interacción y posee los intentos; el catálogo define contenido y SPEC-08 implementa validez acústica.

## 3. Historia de usuario

> Como estudiante, quiero leer las cinco frases y repetir únicamente una muestra no evaluable para poder recibir un informe sustentado.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Secuencia fija de cinco frases y reproducción de referencia.
- Subida de grabación, validación asíncrona, máximo tres intentos por frase e idempotencia.
- Entrega de cinco muestras válidas al orquestador o finalización incompleta.

### Fuera de esta iteración

- Modificar textos, corregir pronunciación en esta etapa, repetir por error fonético o admitir informe con menos de cinco muestras válidas.
- Elegir umbrales acústicos dentro de la UI.

### Supuestos acordados

- Confirmados: un intento inicial y dos repeticiones por frase no evaluable. Como diseño propuesto se procesa una frase/validación a la vez y una frase válida queda cerrada.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S07-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S07-RF-01** (RF-07) — CUANDO la práctica entre en anchors, EL SISTEMA DEBE presentar las cinco frases del snapshot en su orden y permitir escuchar la referencia estadounidense de la frase activa.
- **S07-RF-02** (RF-07, RNF-14) — CUANDO el propietario envíe una grabación de la frase activa, EL SISTEMA DEBE crear un intento numerado y solicitar su validación vinculando práctica, frase, audio y versión del validador.
- **S07-RF-03** (RF-17, RNF-14) — CUANDO el validador confirme voz utilizable, correspondencia con el texto y evaluabilidad de la muestra, EL SISTEMA DEBE aceptarla aunque incluya errores de pronunciación y avanzar a la siguiente frase.
- **S07-RF-04** (RF-17) — SI una frase resulta no evaluable y se han usado menos de tres grabaciones, ENTONCES EL SISTEMA DEBE explicar el motivo y permitir solo los intentos restantes.
- **S07-RF-05** (RF-17) — SI el tercer intento de una frase sigue sin ser evaluable, ENTONCES EL SISTEMA DEBE solicitar al orquestador finalizar incompleta la práctica sin informe y descartar su audio temporal y anclas no publicadas.
- **S07-RF-06** (RF-07, RF-17) — CUANDO existan exactamente cinco frases distintas con una muestra válida cada una, EL SISTEMA DEBE entregar ese conjunto al orquestador para pasar a processing una sola vez.
- **S07-RF-07** (RF-17; contrato con RF-18) — SI se repite una subida o falla la infraestructura durante validación, ENTONCES EL SISTEMA DEBE conservar la identidad del intento y delegar la recuperación al orquestador sin contar la retransmisión como nueva grabación.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S07-CA-01** (S07-RF-01) — Dada conversación cerrada y catálogo V1, Cuando se abra anchors tras publicarse V2, Entonces aparecen las cinco frases de V1 en orden con referencia reproducible y sin otra conversación activa.
- [ ] **S07-CA-02** (S07-RF-02) — Dada una frase abierta, Cuando se envíe audio aceptable en formato, Entonces se obtiene intento pending con vínculos completos y no se puede enviar otra grabación mientras esté pendiente.
- [ ] **S07-CA-03** (S07-RF-03) — Dada muestra con error fonético pero texto cubierto, Cuando el validador la declare evaluable, Entonces queda valid sin solicitar repetición ni consumir una nueva grabación.
- [ ] **S07-CA-04** (S07-RF-04) — Dadas muestras inválidas en intentos uno y dos, Cuando llegue cada resultado, Entonces se informa motivo y quedan dos y una repeticiones respectivamente; no se avanza la frase.
- [ ] **S07-CA-05** (S07-RF-05) — Dados tres intentos inválidos, Cuando finalice el tercero, Entonces no se admite cuarto intento, no existe informe y tras limpieza se ofrece comenzar otra práctica.
- [ ] **S07-CA-06** (S07-RF-06) — Dadas cuatro frases válidas y un evento duplicado, Cuando se procese, Entonces no comienza processing; al llegar la quinta distinta se solicita una única transición con las cinco referencias.
- [ ] **S07-CA-07** (S07-RF-07) — Dado un upload cuya respuesta se perdió y un fallo del modelo, Cuando se reenvíe la misma clave y después se recupere manualmente, Entonces se usa el mismo intento; claves diferentes concurrentes no generan un intento adicional pendiente.

## 7. Diseño técnico y datos

**Datos:** `AnchorAttempt` y cursor de frase activa por práctica. Unicidad de `(practice_id,phrase_id,attempt_number)` y de muestra válida de la frase; el estado de práctica se cambia solo mediante SPEC-04. Conservar la primera muestra válida, eliminar inválidas tras validación salvo la operación recuperable en curso.

**Backend:** POST/GET de intentos en C-03. La subida multipart autentica antes de persistir, llama Audio y encola `Evaluator.validateAnchor`; `422` de formato no crea intento. Un audio aceptado cuya voz/texto no sea evaluable sí cuenta como grabación. Una indisponibilidad técnica no se etiqueta como inválida.

**Eventos:** `anchor.validated` de C-04; el GET de intentos permite recuperar un resultado perdido dentro de la página viva. No consumir un número dos veces ni permitir resubir una frase ya válida.

**Frontend:** muestra «Frase 1 de 5», texto inglés, referencia, grabar/detener y espera con botones bloqueados cuando corresponda. Motivos españoles («No se detectó voz utilizable», «La grabación no cubre la frase»), intentos restantes y acceso a cancelar; no explicar errores fonéticos hasta informe.

**Proxy/local:** subida y canal del origen común; límites de bytes/duración de ADR-003.

**Tecnologías/ADR:** usa transporte de ADR-001 y política `validity_version` de ADR-002; no nuevo modelo ni umbral en navegador.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| SPEC-04 → Frases | Entrar/cancelar fase | Estado y state_version | Estado ajeno a anchors rechaza grabaciones. |
| Frases → SPEC-02/06 | Mostrar y almacenar | AnchorPhrase y Audio.putTemporary | Referencia ausente bloquea contenido; audio ajeno se rechaza. |
| Frases → SPEC-08/C | Validar sin confundir error fonético | Evaluator.validateAnchor; C-05 | Fallo técnico recuperable usa SPEC-04, no gasta repetición. |
| Frases → SPEC-04/09 | Cerrar cinco muestras | IDs válidos y anchor_set_version | Duplicados no completan cardinalidad ni publican. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S07-D-01** — Los límites y suficiencia son RF-17/RNF-14; secuencia de una validación pendiente propuesta el 2026-10-29.

### Preguntas abiertas

- **S07-P-01 — bloqueante G1 para validador real:** Política de validez calibrada y textos/referencias cerrados; C/B con SPEC-01/02 antes de pruebas reales.
- **S07-P-02 — no bloqueante para fixtures:** Ajustar instrucciones de ruido/micrófono según navegador de demo; B antes de G2.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S07-RF-01 → S07-CA-01 | Integración/UI; snapshot y fases. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S07-RF-02 → S07-CA-02 | Contrato/integración; DTO y bloqueo concurrente. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S07-RF-03 → S07-CA-03 | Integración con casos etiquetados; validez independiente de exactitud. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S07-RF-04 → S07-CA-04 | Unidad/UI; conteo y motivos de validez. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S07-RF-05 → S07-CA-05 | Integración; límite, terminal y limpieza. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S07-RF-06 → S07-CA-06 | Contrato/concurrencia; cardinalidad e idempotencia. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| S07-RF-07 → S07-CA-07 | Contrato/fallos; deduplicación y recuperación. | Escenario CA-07 satisfecho y evidencia adjunta al cierre. |
| RF-07 | Recorrido fijo de cinco y versiones | Frases y vínculos de audio correctos. |
| RF-17 | 0/1/2 reintentos, cuarto rechazado y fallo técnico | Conteos, terminales y mismas claves. |
| RNF-14 | Silencio, truncado, texto distinto y error fonético válido | Resultados coherentes con guía calibrada. |
| RNF-09 | Subidas y consultas anónimas/ajenas | No intentos ni bytes de otro propietario. |
| RNF-12 | Flujo completo con teclado y estados anunciados | Texto, intentos y espera comprensibles. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** M: interacción, contador, subida asíncrona y carreras; el validador se consume de C.
- **Riesgos:** Confundir timeout con muestra inválida o duplicar subidas agotaría intentos indebidamente.
- **Consecuencias:** Cinco válidas son condición necesaria; completarlas no garantiza informe si otro procesamiento falla.
