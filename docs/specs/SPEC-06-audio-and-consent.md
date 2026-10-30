# SPEC-06 — Consentimiento y ciclo de vida del audio

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Audio y privacidad  
> **RF relacionados:** RF-09, RF-10, RF-14, RF-20 | **RNF:** RNF-07, RNF-09, RNF-12, RNF-13  
> **RT:** No aplica directamente  
> **Módulo:** Audio y privacidad | **Responsable:** A; B integra consentimiento y C consume audio  
> **Etapa:** E1–E3 | **Iteración:** 1: consentimiento, temporales, anclas y corpus del equipo; 2: recortes, caducidad y reconciliación | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

La práctica usa audio personal y conserva solo frases y recortes autorizados por 30 días. El acceso y la eliminación deben funcionar independientemente de que un enlace viejo o un informe todavía los mencione.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existe política de consentimiento, repositorio privado, metadatos, recortador ni tarea de limpieza. Esta spec posee bytes y vigencia; SPEC-11 coordina solicitudes de borrado entre módulos.

## 3. Historia de usuario

> Como estudiante, quiero conocer y aceptar el uso de mi voz y controlar qué grabaciones puedo escuchar y cuándo dejan de estar disponibles.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Política versionada, aceptación explícita y comprobación previa a capturar/enviar.
- Temporales, frases válidas, recortes mínimos y reproducción privada de usuario/referencia.
- Caducidad, revocación, limpieza física y reconciliación de huérfanos.

### Fuera de esta iteración

- Conservar conversaciones completas, descargar datasets mediante endpoints del producto o compartir audio.
- Implementar eliminación de cuenta y sesión completas fuera del coordinador SPEC-11.

### Supuestos acordados

- Confirmados: consentimiento previo y 30 días desde grabación; envío externo explicado antes de habilitarlo. Plazos operativos de depuración y máximo de recorte se fijan con medición.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S06-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S06-RF-01** (RF-10) — CUANDO el estudiante solicite grabar, EL SISTEMA DEBE exigir una aceptación explícita de la política vigente que indique fines, audio conservado, 30 días y proveedores externos aplicables.
- **S06-RF-02** (RF-10, RNF-07) — CUANDO el sistema reciba audio autorizado, EL SISTEMA DEBE clasificarlo como temporal, frase ancla o recorte y asignarle propietario, origen e instante de captura antes de almacenarlo.
- **S06-RF-03** (RF-14, RF-09) — CUANDO una observación fonética de conversación necesite audio conservado, EL SISTEMA DEBE crear un recorte autorizado del intervalo mínimo con contexto, limitado por la configuración calibrada y vinculado a la evidencia y su referencia estadounidense.
- **S06-RF-04** (RF-09, RNF-09) — MIENTRAS un audio conservado propio esté disponible y no haya vencido, EL SISTEMA DEBE permitir reproducirlo junto con su referencia correspondiente.
- **S06-RF-05** (RF-20, RNF-07) — CUANDO se cumplan 30 días desde la grabación original o se solicite borrar un audio, EL SISTEMA DEBE impedir inmediatamente nuevas lecturas y mostrarlo como vencido o eliminado conservando el texto del informe.
- **S06-RF-06** (RNF-07) — CUANDO una práctica termine, se cancele o falle definitivamente, EL SISTEMA DEBE eliminar su audio completo y temporal y confirmar la limpieza antes de dar por finalizada la operación correspondiente.
- **S06-RF-07** (RNF-07) — SI una caída deja archivos residuales, ENTONCES EL SISTEMA DEBE mantener su acceso revocado y reintentar su eliminación hasta completar la depuración dentro del plazo operativo declarado.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S06-CA-01** (S06-RF-01) — Dada una política sin aceptar, rechazada o cambiada, Cuando se intente crear práctica o transmitir voz, Entonces se bloquea la captura persistida; al aceptar la versión vigente se registra propietario, versión e instante.
- [ ] **S06-CA-02** (S06-RF-02) — Dados bytes válidos y otro usuario que intenta asociarlos a una sesión ajena, Cuando se suban, Entonces solo los propios se almacenan con metadatos y la petición ajena se rechaza antes de persistir.
- [ ] **S06-CA-03** (S06-RF-03) — Dada evidencia con offsets válidos, Cuando se recorte, Entonces audio, fuente, offsets y referencia corresponden al fragmento; un intervalo inválido o equivalente a toda la conversación no se acepta como recorte.
- [ ] **S06-CA-04** (S06-RF-04) — Dado audio disponible y una referencia generada desde su recorte, Cuando el propietario solicite bytes o un rango, Entonces recibe el intervalo correcto; otra cuenta y una petición anónima no reciben ninguno de los dos audios, tampoco por la ruta pública de referencias.
- [ ] **S06-CA-05** (S06-RF-05) — Dado audio un instante antes de caducar y otro recortado días después de grabarse, Cuando venza su plazo original o se borre, Entonces un enlace anterior deja de servir bytes, la UI cambia y el informe textual continúa.
- [ ] **S06-CA-06** (S06-RF-06) — Dados temporales y una frase autorizada, Cuando se complete, cancele o falle, Entonces no quedan temporales ni cachés de audio; solo los conservados permitidos continúan si hay informe completado.
- [ ] **S06-CA-07** (S06-RF-07) — Dado un borrado físico que falla o reinicio entre escritura y metadatos, Cuando corra la reconciliación, Entonces detecta huérfanos y pendientes, no los sirve y deja evidencia de limpieza o un fallo operativo visible.

## 7. Diseño técnico y datos

**Datos:** `ConsentPolicy`, `ConsentRecord`, `AudioAsset`, referencias de origen y operación de limpieza. Bytes privados separados de rutas públicas; cada lectura revalida cuenta, pertenencia, estado y `expires_at`. Solo la referencia del catálogo es pública. La referencia `clip_reference` sintetizada desde texto del estudiante es privada, pertenece a su práctica y vence o se elimina con su recorte fuente, según C-02/C-05/C-06.

**Backend:** C-03 y funciones `Audio.*` de C-05. Validación de tipo, tamaño y duración antes de procesar; el multipart de frases delega almacenamiento aquí. No conservar intentos inválidos más allá de la validación/reintento; si una práctica queda incompleta se descartan también anclas aún no publicadas. La única persistencia autorizada tras éxito son anclas válidas y recortes.

**Eventos:** cambios de disponibilidad alimentan proyección de historial; esta revalida la fuente al leer. Revocación lógica es inmediata, eliminación física tiene tarea idempotente; el ack de finalización de SPEC-04/09 espera limpieza de temporales. Los checkpoints de C-05 permiten reintentar limpieza sin regenerar desde audio eliminado. Los assets candidatos de un informe no publicado se eliminan si termina incompleta la práctica.

**Frontend:** consentimiento no preseleccionado, explicación de uso y plazo, reproductores con «Escuchar mi audio» / «Escuchar referencia», estados «Audio vencido» / «Audio eliminado». Si cambia proveedor/política durante una práctica, no enviar a un proveedor no aceptado; cerrar o volver al flujo permitido conforme SPEC-04, sin cambiar de ruta en silencio.

**Proxy/local:** bytes por `/api/v1/audio/:id`; ninguna carpeta privada montada como estática. Ranges también autorizados; caché no-store. En red, canal cifrado.

**Tecnologías/ADR:** almacenamiento privado local para demo y recorte de audio son propuestas; A elige herramienta según formatos de ADR-001. ADR-003 fija recorte máximo, limpieza, temporales de herramientas y recuperación tras caída; C verifica calidad acústica.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| SPEC-04/05/07 → Audio | Autorizar y guardar | ConsentRecord y Audio.putTemporary | Política obsoleta/bytes inválidos bloquean captura o persistencia. |
| SPEC-08/09 → Audio | Leer evidencia, recortar y finalizar | readForJob, retainClip, finalize; C-05 | Revocación/epoch invalida trabajo; no guardar copias propias. |
| SPEC-10/11 → Audio | Mostrar vigencia y borrar | AudioAsset y operación idempotente | Proyección vieja no concede acceso; fallo físico mantiene revocación. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S06-D-01** — RF-10/RNF-07 fijan consentimiento y 30 días; metadatos y ack son diseño propuesto el 2026-10-29.

### Preguntas abiertas

- **S06-P-01 — bloqueante G1:** Aprobar texto de consentimiento y proveedores reales antes de procesar voz; A con B/C. El texto describe la retención real de cada iteración: en la 1, corpus interno del equipo sin caducidad automática (D-16); los 30 días solo se prometen cuando la caducidad esté implementada.
- **S06-P-02 — bloqueante para recortes reales (iteración 2):** Fijar límites de carga/recorte y plazo de depuración con medición; A/C, ADR-003.
- **S06-P-03 — no bloqueante para almacenamiento local:** Si se elige proveedor externo, verificar política de retención/eliminación y describir sus límites antes de habilitarlo; A/C antes de G1.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S06-RF-01 → S06-CA-01 | UI/contrato; aceptación y rechazo en servidor. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S06-RF-02 → S06-CA-02 | Integración; clasificación, formato/tamaño y pertenencia. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S06-RF-03 → S06-CA-03 | Integración/audio; duración, offsets y escucha del fragmento. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S06-RF-04 → S06-CA-04 | Contrato/reproducción; permisos también en rangos. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S06-RF-05 → S06-CA-05 | Reloj controlado/UI; fronteras de caducidad y fecha original. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S06-RF-06 → S06-CA-06 | Integración/inspección; inventario de bytes y ack. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| S06-RF-07 → S06-CA-07 | Fallo/reinicio; inventario y registro de reconciliación. | Escenario CA-07 satisfecho y evidencia adjunta al cierre. |
| RF-09, RF-14 | Reproducir referencia/recorte y verificar offsets | Audio pertinente sin conversación completa. |
| RF-10 | Política, aceptación, cambio y peticiones directas | Ningún audio procesado sin consentimiento válido. |
| RF-20, RNF-07 | Reloj, borrado, reinicio y disco residual | No acceso tras vencimiento y evidencia de limpieza. |
| RNF-09 | Dos cuentas y rangos de audio | 404/401 sin bytes. |
| RNF-12 | Consentimiento y reproductores con teclado | Etiquetas/estados en español. |
| RNF-13 | Revisión de transporte y rutas estáticas | Audio privado solo por control autenticado. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** L: almacenamiento, consentimiento, recortes, expiración y recuperación; implementar temporal/lectura primero y recortes después.
- **Riesgos:** Copias en cachés, temporales del recortador, fechas reiniciadas al generar clip y tareas tardías; requiere inspección del sistema de archivos real.
- **Consecuencias:** El informe puede conservarse sin audio; los bytes eliminados no se reconstruyen a partir de tareas antiguas.
