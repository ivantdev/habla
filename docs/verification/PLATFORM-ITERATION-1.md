# Verificación de plataforma · Iteración 1

**Fecha** · 17 de noviembre de 2026. **Entorno** · Windows, Python 3.12 y Node.js 24.

**Perfil** · C-09 con señales sintéticas. Alcance del rol A según el [plan por iteraciones](../ROADMAP.md).

Las pruebas de [backend](../../tests/test_platform.py) y del [consumidor web](../../web/tests/contract.test.js) usan los contratos de la misma versión. Pasaron 20 casos de backend, 2 del consumidor y los 24 originales del [spike de audio](../../spikes/audio-channel/README.md), ejecutado con sus propias dependencias. El cliente compiló con Vite.

| Spec y criterios | Evidencia en el perfil simulado |
| --- | --- |
| SPEC-00 · S00-CA-01 a S00-CA-05 | Dependencias resueltas con lockfiles, arranque en dos procesos de desarrollo y sonda HTTP por el proxy. Ambos consumidores aceptan los fixtures v1 y rechazan un estado desconocido. Dos consultas de fixtures devuelven los mismos datos. La interfaz identifica el modo y el backend exige el alias al habilitar corpus. Pruebas de rechazo de origen en HTTP y WS. |
| SPEC-04 · S04-CA-02 a S04-CA-07 | Dos solicitudes concurrentes producen una reserva. El historial carga con el cupo ocupado. Reloj controlado justo antes y al llegar a 300/600 s. Conflicto con versión obsoleta. Desconexión, cancelación durante procesamiento y reinicio liberan el cupo. Reintento manual con el mismo incidente y el plazo original. Un segundo fallo o el vencimiento termina en `incomplete`. |
| SPEC-06 · S06-CA-02, S06-CA-04, S06-CA-06 y D-16 | Audio de ancla validado antes de almacenar. Los rangos de anclas completadas devuelven `206` y `no-store`. Los temporales desaparecen tras completar, cancelar o fallar con corpus desactivado. Con corpus activo se archivan PCM, anclas inválidas, transcripción e informe o evidencia disponible. Se verifica el alias original tras reinicio y la ausencia de ruta pública al corpus. |
| SPEC-09 · S09-CA-01 a S09-CA-06 | Un borrador privado pasa la validación de esquema, versiones, cobertura, intervalos, evidencia y referencias. El filtro descarta una cita inventada, una del tutor y una referencia de catálogo inexistente. Un fallo de limpieza o commit mantiene el informe privado y permite completar con el borrador guardado. Una cancelación con evaluación pendiente impide el commit. |
| SPEC-10 · S10-CA-01, S10-CA-02, S10-CA-04 y S10-CA-05 | Paginación de un propietario, reproducción de anclas, comparación por sonido y oportunidades excluidas aparte. Se rechazan pares iguales, incompletos, desconocidos o con calibración distinta. |
| SPEC-12 · S12-CA-01, S12-CA-03 y S12-CA-06 | Modos de fallo comprobados con datos sintéticos. El tercer intento inválido produce cierre y se rechaza el cuarto. Reiniciar con una práctica no terminal y un archivo huérfano limpia los bytes y permite crear otra práctica. |

El navegador de escritorio abrió la práctica por teclado y mostró el turno del estudiante y del tutor recibidos por WebSocket a través de Vite. Al recargar, la práctica figuró incompleta en el historial. Se abrieron dos sesiones completadas con el reloj de pruebas. El reproductor leyó la duración de un WAV sintético de 320 ms y la tabla del par mostró los denominadores y las oportunidades sin evaluar.

Se registraron marcas de simulación de primer frame del tutor e informe listo. Los criterios de calidad y latencia con voz pertenecen al [protocolo de métricas](../experiments/METRICS.md).

## Pendiente de integración

- G0/G1 requiere revisión conjunta de [ADR-001](../architecture/ADR-001-local-development.md), publicación del catálogo y referencias de Nicolás, acuerdo D-18, conexión de los adaptadores de voz y validación de Ivan, y cierre de la ventana de conversación y los plazos reales en [ADR-003](../architecture/ADR-003-fixture-operation.md).
- G2 requiere dos recorridos con voz, informes reales, reproducción, comparación y mediciones en el PC de Ivan. La verificación del micrófono, la parada audible y la fluidez con modelos pendientes se completa en ese entorno.
- Cuentas, consentimiento para personas externas, recuperación de canal con idempotencia, caducidad y acceso al auditorio figuran en la iteración 2. Los criterios de dos propietarios, recortes y borrado se verifican en el hito que los incorpora.
