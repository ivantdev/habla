# Especificación de métricas de evaluación

**Estado:** propuesta, 2026-10-30. **Responsable de ejecución:** Ivan (C, [SPEC-01](../specs/SPEC-01-experiments-and-evaluator-selection.md)). **Anotaciones humanas:** Nicolás (B). **Plan:** [iteraciones](../ROADMAP.md).

Este documento fija qué se mide, cómo se calcula y qué se reporta, para que los resultados sean reproducibles y comparables. Los datos marcados **por verificar** se confirman al descargar los conjuntos; no se reportan como hechos antes de esa comprobación.

## 1. Reglas comunes

- **Particiones por hablante** (RT-03): entrenamiento, validación y prueba sin hablantes compartidos. Prueba se usa una sola vez, al final, con el modelo y el umbral congelados.
- Todo ajuste (umbral, hiperparámetros, prompts) se hace en validación.
- Cada resultado registra: conjunto y versión, partición, modelo y versión, umbral, fecha, hardware y comando para reproducirlo.
- Se reportan conteos absolutos junto a cada porcentaje, e intervalos de confianza al 95 % por *bootstrap* remuestreando hablantes.
- Una meta no alcanzada se reporta tal cual (RNF-03); no se cambia la métrica para cumplirla.
- Los resultados sobre el corpus del equipo (D-16) se reportan aparte de los datos públicos y no sustentan afirmaciones sobre acento colombiano ni eficacia pedagógica.

## 2. Detección de errores fonéticos (RNF-03, RT-02, RT-04)

Unidad: cada fonema esperado alineado con la secuencia canónica.

| Caso | Anotación humana | Sistema |
| --- | --- | --- |
| Verdadero rechazo (TR) | Error | Marca error |
| Falso rechazo (FR) | Correcto | Marca error |
| Falsa aceptación (FA) | Error | No marca |
| Verdadera aceptación (TA) | Correcto | No marca |

- **Precisión** = TR / (TR + FR). De lo que el sistema señala, qué parte es un error real. **Meta: ≥ 0,70 en validación** y prioridad sobre el recall.
- **Recall** = TR / (TR + FA). De los errores reales, qué parte se detecta.
- **F1** = 2·P·R / (P + R), solo como resumen.
- **Precisión de diagnóstico** = TR con el fonema observado correcto / TR, cuando el método predice qué sonido se produjo.
- **Selección del umbral:** en validación, el umbral con mayor recall que mantiene precisión ≥ 0,70. Si ninguno la alcanza, se elige el de mayor precisión y se documenta. Se entrega la curva precisión-recall.
- **Sin detecciones:** la precisión es indefinida y la meta no se considera cumplida.
- **Líneas base:** GOP con umbral fijo elegido en validación; Azure Pronunciation Assessment si hay acceso. Si un servicio solo da puntuaciones agregadas, se documenta y no se equipara con detección por fonema (RT-04).
- **Desgloses:** por conjunto, por L1 (incluido el subconjunto hispanohablante de L2-ARCTIC) y por tipo de error (sustitución, omisión, inserción).

### Conjuntos

| Conjunto | Uso | Etiqueta de error | Por verificar |
| --- | --- | --- | --- |
| L2-ARCTIC | Entrenamiento, validación y prueba | Anotaciones de sustitución, omisión e inserción | 24 hablantes de 6 L1 con ~150 enunciados anotados por hablante; licencia de uso académico; partición de prueba frecuente en la literatura: NJS, TLV, TNI, TXHC, YKWK, ZHAA; hablantes de L1 español |
| speechocean762 | Prueba con otra L1 (mandarín) | Puntuación por fonema 0–2: se toma **error = 0**; el 1 (acento marcado) no cuenta como error, según RNF-06. Sensibilidad adicional con error ≤ 1 | Licencia y número de hablantes |

## 3. Validez de frases ancla (RNF-14, RF-17)

Conjunto de validación con muestras válidas y degradadas: silencio, audio truncado, ruido de fondo, frase distinta a la solicitada y frases leídas con errores de pronunciación.

- **Tasa de falso inválido:** muestras válidas rechazadas. Es la más importante, porque consume reintentos del estudiante.
- **Tasa de falso válido:** muestras no evaluables aceptadas.
- Exactitud por motivo de invalidez. Una frase con errores de pronunciación debe resultar **válida**.

## 4. Incertidumbre en conversación (RNF-05) — iteración 2

- **Cobertura:** porcentaje de palabras evaluadas frente a excluidas por confianza baja del ASR.
- Precisión de detección solo sobre palabras evaluadas, para cada umbral de confianza. Se elige el umbral en validación.

## 5. Reconocimiento de voz

- **WER** de Whisper sobre L2-ARCTIC (validación) y sobre una muestra de turnos del corpus del equipo (D-16) transcrita a mano por Nicolás.

## 6. Informe (RNF-04, RT-05, RT-06)

- **Validez estructural (automática):** toda cita de gramática o vocabulario existe literalmente en un turno final; toda observación de pronunciación referencia evidencia acústica existente. Meta: 100 %; una observación inválida no se publica.
- **RT-05, comparación con línea base:** el mismo LLM solo con la transcripción de Whisper. Se mide el porcentaje de observaciones sustentadas y el número de errores atribuidos sin evidencia en cada versión.
- **RT-06, precisión lingüística:** Nicolás anota las transcripciones y se calcula, por categoría (gramática y vocabulario), precisión = observaciones correctas / observaciones emitidas, y recall cuando el anotador marque errores omitidos.
  - Muestra propuesta: 20 sesiones del corpus del equipo (D-16) o al menos 150 observaciones.
  - Si otro integrante anota un 20 % de la muestra, se reporta el acuerdo (kappa de Cohen). Si no, se declara como limitación que hay un único anotador.
  - La meta numérica la fija el equipo antes de medir; no se inventa.
- **Criterio pedagógico (RNF-06):** la guía de anotación marca como error solo lo que cambia el significado o dificulta la comprensión.

## 7. Latencia (RNF-01)

Se registran marcas de tiempo en servidor y navegador; al menos 100 turnos por configuración, en el PC de demo con una sesión activa.

| Métrica | Desde | Hasta | Referencia |
| --- | --- | --- | --- |
| Respuesta del tutor | Fin de la voz del estudiante (VAD) | Primer audio audible del tutor | p95 < 2 s (propuesta, no límite acordado) |
| Reacción a interrupción | Inicio de la voz del estudiante | Parada de la reproducción | Por fijar tras medir |
| Espera del informe | Quinta frase válida | `report.ready` | Por fijar tras medir |

Se reportan p50, p95 y máximo, junto con hardware, modelos y su cuantización.

## 8. Adecuación del tutor (RNF-08, RF-05)

Casos escritos por Nicolás y revisados por Ivan: por tema y nivel, peticiones dentro del tema, temas sensibles y peticiones de consejo médico, legal o emocional.

- Porcentaje de respuestas que cumplen la ficha y los límites, según una lista de comprobación.
- Porcentaje de turnos con correcciones durante la charla. Meta: 0 %.

## 9. Entregables y fechas

| Entregable | Iteración |
| --- | --- |
| Particiones, licencias y protocolo registrados en `docs/experiments/` | 1, semana 1 |
| Precisión y recall en validación con el umbral elegido; línea base GOP | 1, semana 3 |
| Acumular sesiones en el corpus del equipo | 1, desde la semana 3 |
| Guía de anotación y primeras anotaciones | 1, semana 4 |
| Resultados en prueba, RT-05, RT-06, latencias, tutor y comparación con Azure | 2, antes del pitch |
