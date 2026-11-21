# ADR-003 — Operación del perfil C-09

**Estado** · Parámetros para el entorno simulado. Los plazos de inferencia real quedan para G1 con Nicolás e Ivan.

**Alcance** · S04-P-02, S06-RF-02/06, C-07, C-09, D-16, D-17 y D-18.

## Plazos y limpieza

| Parámetro | Valor del fixture |
| --- | --- |
| Reserva inicial | 30 s de margen para negociar y arrancar. Una práctica en `ready` mantiene el cupo durante esa ventana. |
| Conversación | 300 o 600 s desde el arranque, con reloj monotónico del servidor. La implementación simulada corta captura y generación al vencer y avanza a anclas. |
| Negociación o subida | 10 s. Cada ancla se envía como WAV PCM mono de 16 kHz, hasta 15 s de muestras. |
| Trabajo de modelo | 10 s por operación de fondo del fixture. |
| Recuperación | 30 s para un reintento manual del incidente. Si se recupera una charla cuyo reloj venció, entra en anclas con el fin ya registrado. |
| Cierre de canal | `incomplete` y limpieza, conforme a D-17. Tras arrancar, se aplica la misma transición a prácticas no terminales. |

La publicación guarda un borrador validado, copia al corpus si está habilitado, elimina los temporales y confirma la versión antes del commit de `completed` y `report_id`. Si falla el commit, el mismo borrador permite reintentar. Cancelar revoca la práctica y las muestras antes de limpiar. Si el sistema de archivos devuelve un error, la limpieza se vuelve a intentar dentro del proceso y se reconsidera al arrancar.

La telemetría registra transiciones, latencia de encolado del primer frame, tratamiento de interrupción en servidor y tiempo desde la quinta muestra válida hasta emitir `report.ready`. Las mediciones de primera salida audible, parada audible y percentiles de [METRICS §7](../experiments/METRICS.md#7-latencia-rnf-01) se obtienen en el PC de Ivan con los modelos integrados.

## Configuración local

| Variable | Por defecto | Uso |
| --- | --- | --- |
| `HABLA_DATA_DIR` | `data/` | Directorio privado de SQLite, bytes de audio y corpus opcional. Se admite una ruta fuera del checkout. |
| `HABLA_MODE` | `fixture` | `fixture` o `demo`, ambos con datos sintéticos. |
| `HABLA_DEMO_SCENARIO` | `normal` | Una condición de la tabla siguiente. Los escenarios de fallo requieren `HABLA_MODE=demo`. |
| `HABLA_CORPUS_ENABLED` | `0` | Con `1`, archiva en `data/corpus/<práctica>/` antes de limpiar. La ubicación sigue a `HABLA_DATA_DIR`. |
| `HABLA_CORPUS_MEMBER` | — | Obligatoria si el corpus está activo. Alias del integrante en el manifiesto, con letras ASCII, números, guión o guión bajo. |

El corpus reproduce D-16 con datos sintéticos. El alias de recolección se fija al crear la práctica, también para recuperar el manifiesto tras un reinicio. El manifiesto conserva transcripción, intentos incluidos los inválidos, datos de las grabaciones, informe disponible y evidencia, incluso si falla la etapa de informe. El audio de conversación se guarda como PCM s16le mono con frecuencia registrada en el manifiesto. Las anclas son WAV. El recorrido de aceptación de limpieza usa `HABLA_CORPUS_ENABLED=0`. Una futura ejecución con audio del equipo aplica el acuerdo escrito D-18 y la política de custodia de D-16.

| Escenario de demo | Comportamiento |
| --- | --- |
| `anchor_invalid` | Tres muestras inválidas cierran la práctica. |
| `anchor_fail_once` | El reintento manual recupera el mismo intento de ancla. |
| `asr_fail_once`, `tutor_fail_once`, `tts_fail_once` | El paso simulado falla al primer intento y vuelve tras la recuperación manual. |
| `report_fail_once`, `report_unavailable` | Fallo inicial o persistente al construir el informe. |
| `commit_fail_once` | Fallo al publicar después de la limpieza. El reintento utiliza el borrador guardado. |
| `slow_evaluation` | Espera asíncrona para probar cancelación y consultas durante el procesamiento. |
