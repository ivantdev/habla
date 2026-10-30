# SPEC-01 — Protocolo experimental y selección del evaluador

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Evaluación  
> **RF relacionados:** RF-06 | **RNF:** RNF-01, RNF-03, RNF-05, RNF-06, RNF-14  
> **RT:** RT-02, RT-03, RT-04, RT-05, RT-06, RT-07  
> **Módulo:** Evaluación | **Responsable:** C; A revisa operación y B contenido  
> **Etapa:** E0–E3 | **Iteración:** 1: protocolo y evaluador GOP en validación; 2: clasificador entrenado frente a GOP, prueba final, Azure, RT-05 y RT-06 | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

La evaluación acústica es el riesgo principal. El catálogo exige comparar prototipo propio y alternativa de Microsoft, con datos públicos y mediciones reales, antes de seleccionar el evaluador. No hay evidencia todavía de que un servicio entregue el nivel fonético requerido.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existen datasets preparados, particiones, modelos calibrados, acceso verificado a proveedor ni mediciones. Esta spec produce artefactos y decisiones reproducibles, no endpoints públicos.

## 3. Historia de usuario

> Como equipo del proyecto, quiero medir alternativas sobre datos comparables para escoger un evaluador que sustente los informes y conocer sus límites.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro del alcance de la spec

- Protocolo, licencias verificadas, manifiestos y separación por hablante.
- Prototipo propio, comparación externa cuando sea accesible y GOP donde sea aplicable.
- Calibración de confianza/validez y medición de calidad, latencia y recursos.
- Comparación de informes acústicos frente a texto solo y revisión humana de gramática/vocabulario.

### Fuera del alcance de la spec

- Piloto longitudinal, participantes propios, certificación y afirmaciones de eficacia pedagógica. El corpus interno del equipo (D-16) no es un estudio con participantes.
- Garantizar una precisión no observada o escoger el umbral con prueba.

### Supuestos acordados

- Confirmados: orientación a pesos abiertos, referencia estadounidense, datos públicos y objetivo de precisión 0,70 en validación. Dataset y capacidades concretas siguen pendientes.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S01-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S01-RF-01** (RT-03, RT-07) — CUANDO se incorpore un conjunto público, EL SISTEMA DEBE registrar su versión, procedencia, licencia, etiquetas y partición por hablante antes de usarlo en experimentos.
- **S01-RF-02** (RNF-03) — CUANDO se calibre el detector, EL SISTEMA DEBE seleccionar el umbral únicamente con validación y reportar precisión, recall y conteos con el objetivo de precisión de al menos 0,70.
- **S01-RF-03** (RT-02, RT-04) — CUANDO se compare el prototipo con un servicio externo, EL SISTEMA DEBE declarar la equivalencia de tarea, ejemplos y etiquetas y registrar cualquier acceso o salida no disponible.
- **S01-RF-04** (RNF-03, RT-03) — CUANDO se evalúe el modelo congelado en prueba, EL SISTEMA DEBE reportar precisión y recall reales, conteos y versiones sin reajustar el umbral con esos resultados.
- **S01-RF-05** (RNF-01) — CUANDO se mida el prototipo de voz e informe, EL SISTEMA DEBE registrar tiempos de respuesta audible, interrupción e informe con percentiles y condiciones de hardware, red, navegador y carga.
- **S01-RF-06** (RNF-05, RNF-06, RNF-14) — CUANDO se definan las políticas de validez, confianza y error pedagógico, EL SISTEMA DEBE versionar los criterios y sus resultados sobre silencio, ruido, audio truncado, cobertura y diferencias de acento comprensibles.
- **S01-RF-07** (RT-05, RT-06) — CUANDO se evalúen los informes, EL SISTEMA DEBE comparar la variante acústica con la variante de texto solo y reportar precisión por categoría lingüística frente a anotaciones humanas.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S01-CA-01** (S01-RF-01) — Dado un dataset candidato, Cuando se prepare, Entonces existe manifiesto con permisos comprobados y una inspección que encuentra cero hablantes compartidos entre entrenamiento, validación y prueba.
- [ ] **S01-CA-02** (S01-RF-02) — Dadas predicciones de validación con y sin detecciones, Cuando se seleccione el umbral, Entonces el informe distingue meta lograda/no lograda y no declara cumplimiento cuando no hay detecciones.
- [ ] **S01-CA-03** (S01-RF-03) — Dado un proveedor inaccesible o con notas agregadas, Cuando se documente la comparación, Entonces se identifica la limitación sin inventar métricas fonéticas ni una comparación realizada; GOP se incluye o se justifica su inaplicabilidad.
- [ ] **S01-CA-04** (S01-RF-04) — Dados modelo y umbral congelados, Cuando se ejecute prueba, Entonces el manifiesto conserva sus hashes y reporta resultados incluso si la meta no se alcanza.
- [ ] **S01-CA-05** (S01-RF-05) — Dada una sesión real y un conjunto de repeticiones definido antes de medir, Cuando se capture rendimiento, Entonces se reportan tamaño de muestra, fallos, percentiles y condiciones sin adoptar los dos segundos como límite acordado.
- [ ] **S01-CA-06** (S01-RF-06) — Dadas muestras con silencio y con pronunciación errónea pero evaluable, Cuando se aplique la política, Entonces la primera es inválida y la segunda sigue siendo válida; las unidades dudosas quedan no evaluadas.
- [ ] **S01-CA-07** (S01-RF-07) — Dada una muestra con referencias humanas preparadas (corpus del equipo, D-16) y protocolo fijado, Cuando se comparen variantes, Entonces se reportan observaciones sustentadas, atribuciones sin evidencia y precisión separada de gramática/vocabulario con denominadores.

## 7. Diseño técnico y datos

**Ubicación/datos:** experimentos fuera de datos productivos; manifiestos incluyen identificadores de hablante, versión, licencia, configuración y hashes, sin redistribuir audio cuya licencia no lo permita.

**Interfaces:** produce el perfil `evaluator_version/calibration_version/validity_version` de C-05, una lista de capacidades y fixtures. SPEC-08 implementa el adaptador; esta spec decide con evidencia. No endpoints ni eventos de usuario.

**Frontend:** no pantalla nueva; B consume las limitaciones aprobadas para las vistas de evaluación.

**Proxy/local:** ejecución interna/offline en entorno registrado; no exponer notebooks ni datasets por el proxy web.

**Tecnologías/ADR:** Whisper, wav2vec2, GOP, L2-ARCTIC, speechocean762 y Microsoft son candidatos del catálogo, con compatibilidad y licencias por comprobar. ADR-002 debe justificar calidad, evidencia, costo, acceso, latencia y memoria. La decisión preliminar en G1 habilita adaptación; la decisión final y métricas congeladas se cierran en G3.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| C → SPEC-02/B | Cubrir sonidos y definir anotación | Conjunto de frases y guía versionada | Frases sin cobertura bloquean aceptación, no fixtures. |
| C → SPEC-00/A | Usar entorno real y registrar recursos | Configuración y telemetría sin audio en logs | Sin GPU/acceso se documenta bloqueo experimental. |
| SPEC-08/09 → C | Ejecutar alternativas y medir informes | C-05/C-06 con versiones congeladas | Resultado no comparable se excluye justificadamente. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S01-D-01** — Objetivo 0,70 y datos públicos provienen de RNF-03/RT-07 (catálogo del 2026-10-28). No se aprueba un motor en esta planificación.

### Preguntas abiertas

- **S01-P-01 — bloqueante G1 para modelos reales:** Acceso/licencias, tamaño de muestra, motor preliminar, umbrales de validez de anclas y guía fonética de RNF-06; C con B, antes de conectar evaluación real. La guía de anotación lingüística de RT-06 se cierra en la semana 4 y el indicador ASR con su umbral de confianza (RNF-05) en la iteración 2. Las métricas están especificadas en [METRICS.md](../experiments/METRICS.md).
- **S01-P-02 — bloqueante G3:** Cerrar selección, umbrales de latencia, recortes, precisión lingüística y criterio pedagógico; C con B/A, antes de aceptación. La meta numérica lingüística no se inventa.
- **S01-P-03 — no bloqueante para otros módulos:** Disponibilidad y presupuesto de la alternativa externa; C/A, investigar durante E0 y registrar limitación si no hay acceso.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S01-RF-01 → S01-CA-01 | Inspección/automatización de datos; manifiesto y auditoría de solapamientos. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S01-RF-02 → S01-CA-02 | Evaluación; umbral, TP/FP/FN y conjunto de validación. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S01-RF-03 → S01-CA-03 | Experimento/inspección; tabla de comparabilidad y evidencia de acceso. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S01-RF-04 → S01-CA-04 | Evaluación reproducible; configuración congelada y reporte. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S01-RF-05 → S01-CA-05 | Rendimiento; trazas y resumen de condiciones. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S01-RF-06 → S01-CA-06 | Evaluación; guía, casos etiquetados y matriz de errores. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| S01-RF-07 → S01-CA-07 | Evaluación; anotaciones, resultados por variante y límites. | Escenario CA-07 satisfecho y evidencia adjunta al cierre. |
| RF-06 | Comprobar que los experimentos reciben audio y no solo transcripción | Evidencia acústica exportable. |
| RNF-01 | Protocolo de percentiles con fallos incluidos | Datos y resultados por configuración. |
| RNF-03 | Evaluación congelada | TP, FP, FN y denominadores. |
| RNF-05, RNF-06, RNF-14 | Guía y pruebas de muestras etiquetadas | Umbrales/versiones y errores de validez. |
| RT-02, RT-03, RT-04, RT-07 | Auditoría de datos y comparabilidad | Manifiestos y alternativas verificadas. |
| RT-05, RT-06 | Comparación de variantes y anotación humana | Precisión por categoría y atribuciones sin evidencia. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** L: datos, etiquetado, prototipos, calibración y medición final. Dividir internamente en protocolo E0, calibración E1 y evaluación congelada E3.
- **Riesgos:** Licencias, acceso externo, etiquetado costoso, memoria GPU y dominio distinto al público; reservar tiempo de C sin asignarle infraestructura adicional.
- **Consecuencias:** Las limitaciones observadas se publican; una meta incumplida no se oculta ni se transforma en requisito satisfecho.
