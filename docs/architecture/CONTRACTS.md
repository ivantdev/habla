# Contratos de integración v1

**Estado:** propuesta para congelar en G0. **Fecha:** 2026-10-29; C-09 del 2026-10-30. **Custodios:** A (API, identidad, estado y audio), B (contenido, conversación e intentos), C (evaluación e informe). Referencias: [arquitectura](ARCHITECTURE.md), [plan](../specs/README.md).

Este documento concentra las definiciones compartidas. Las specs describen el comportamiento y remiten a estos contratos. Los DTO son independientes de lenguaje, tablas y proveedor. No se exponen rutas de archivos ni claves del almacenamiento.

## C-01. Convenciones HTTP y seguridad

- Base `/api/v1`; JSON UTF-8 salvo bytes de audio. IDs opacos como cadenas, instantes UTC ISO 8601 y duraciones/intervalos en milisegundos. Todas las ventanas son `[start_ms, end_ms)`.
- Autenticación propuesta: cookie de sesión opaca `HttpOnly`, `Secure` en red y `SameSite`; vida e invalidación en ADR-001. Mutaciones requieren protección CSRF y validación del origen. Validar `Origin` también al abrir el canal; no incluir tokens en URL.
- El servidor obtiene `owner_id` desde la identidad, nunca desde el cuerpo enviado por el cliente. Recursos ajenos o borrados responden `404`; falta de autenticación `401`.
- Error `{error:{code,message,request_id,retryable,details?}}`; `message` en español. `400` petición malformada, `409` conflicto de estado/cupo/clave idempotente, `413` tamaño, `415` formato, `422` campos o muestra inválidos, `429` límite declarado en configuración, `503` dependencia indisponible, `504` deadline. No filtrar datos privados en `details`.
- `POST` que crea prácticas, consentimientos, intentos, reintentos o tareas, y `DELETE` que solicita eliminar datos, usan `Idempotency-Key`. Alcance `(owner_id,ruta,key)`. Misma clave y contenido devuelve el mismo recurso sin consumir otro intento; contenido distinto devuelve `409 IDEMPOTENCY_CONFLICT`. La clave se conserva al menos durante la vida de la operación y sus reintentos, según ADR-003. Borrados repetidos con la misma clave no recrean recursos ni fallan por ausencia del recurso propio ya eliminado.
- Listados `?cursor=<opaco>&limit=20`, máximo propuesto 100, respuesta `{items:[],next_cursor:null|cadena}`; orden `(created_at desc,id desc)` estable. El backend revalida pertenencia al resolver un cursor.
- Las respuestas con información personal, informes y audio usan `Cache-Control: no-store`. No se sirven archivos privados por una ruta estática ni enlaces públicos duraderos.

## C-02. DTO comunes

| DTO | Campos requeridos y semántica |
| --- | --- |
| `AccountView` | `id,email,created_at`; nunca hash ni sesión secreta |
| `ConsentPolicy` | `version,purposes,retention_days=30,external_processors[]`; uso acústico y conservación explícitos |
| `ConsentRecord` | `id,owner_id,policy_version,accepted_at,external_processors[]`; aceptación explícita, no casilla preseleccionada |
| `Catalog` | `version,levels=[A2,B1,B2],topics[],anchor_set_version,anchors[],tutor_policy_version,tutor_policy` |
| `Topic` | `id` en `restaurant,job_interview,weekend,travel,news`; `label_es,objectives_by_level` |
| `AnchorPhrase` | `id,position` 1..5, `text_en,reference_audio_id,target_sounds[]` |
| `Practice` | `id,created_at,level,topic_id,duration_seconds` 300 o 600, `status,state_version,reason_code?,conversation_started_at?,conversation_ends_at?,catalog_version,anchor_set_version,evaluator_version?,report_id?` |
| `Operation` | `id,type,status` en `pending,running,succeeded,failed`, `resource_id?,error?`; no implica permiso para ver otro recurso |
| `AudioAsset` | `id,practice_id?,source` en `conversation_temp,anchor,conversation_clip,reference,clip_reference`, `captured_at,expires_at?,status,media_type,duration_ms,source_asset_id?,source_start_ms?,source_end_ms?` |
| `Turn` | `id,practice_id,sequence,speaker` en `student,tutor`, `text,status` en `partial,final,interrupted`, `audio_id?,start_ms,end_ms,word_confidence?,heard_until_ms?` |
| `AnchorAttempt` | `id,practice_id,phrase_id,attempt_number` 1..3, `audio_id,status` en `pending,valid,invalid`, `invalid_reason?,validity_version` |

No se retorna `owner_id` en vistas públicas que no lo necesiten. El registro interno de práctica incluye `owner_id,consent_id,web_session_id,client_instance_id,lease_id,deletion_epoch` además de la vista pública: debe poder demostrar qué aceptación autorizó el audio y revocar el canal correcto. `deletion_epoch` es un token interno de concurrencia, no un control que el cliente pueda modificar. `AudioAsset.status`: `pending,available,expired,deleted`; los temporales no se exponen en historial. `captured_at` de un recorte procede de la grabación original, nunca de la fecha de recorte; `expires_at=captured_at+30 días` para audio conservado de usuario.

`reference` identifica exclusivamente las referencias públicas del catálogo, sin práctica ni datos personales. `clip_reference` es una referencia generada desde un fragmento del estudiante: tiene propietario y práctica, comparte vencimiento con el recorte de origen y se elimina al borrar ese recorte, sesión o cuenta. Sus bytes usan `/audio/:id` autenticado; nunca la ruta pública de referencias.

## C-03. Operaciones públicas y autoridad

| Operación | Petición / resultado nominal | Propietario y errores particulares |
| --- | --- | --- |
| `POST /accounts` | `{email,password}` → `201 AccountView` | Identidad; `422` formato/política, `409 EMAIL_UNAVAILABLE` |
| `POST /auth/sessions` | `{email,password}` → `200 AccountView` + cookie | Identidad; `401 INVALID_CREDENTIALS` |
| `GET /auth/me` | → `200 AccountView` | Identidad; `401` |
| `DELETE /auth/session` | → `204`, invalida cookie y sesión servidor | Identidad; repetición `204` |
| `GET /catalog` | → `200 Catalog` con cinco frases y política del tutor | Contenido; lectura sin grabación |
| `GET /consent-policy` | → `200 ConsentPolicy` | Audio; versión vigente |
| `POST /consents` | `{policy_version,accepted:true}` → `201 ConsentRecord` | Audio; `409 POLICY_CHANGED`, `422` aceptación ausente |
| `POST /practices` | `{level,topic_id,duration_seconds,consent_id,catalog_version}` → `201 Practice(ready)` | Orquestación; `409 SERVER_BUSY/POLICY_CHANGED`, `422` selección; no acepta `owner_id` |
| `GET /practices/:id` | → `200 Practice` | Orquestación; `404` ajeno |
| `POST /practices/:id/start` | `{state_version}` → `200 Practice(conversation)` | Orquestación; requiere canal/preflight y lease vigentes |
| `POST /practices/:id/cancel` | `{state_version}` → `202 Operation` | Orquestación; bloquea captura y publicación antes de responder |
| `POST /practices/:id/retry` | `{operation_id,state_version}` → `202 Operation` | Orquestación; una recuperación manual por incidente, `409 RETRY_EXHAUSTED/STATE_CONFLICT` |
| `POST /practices/:id/anchor-attempts` | metadatos `phrase_id,state_version` y bytes, multipart → `202 AnchorAttempt(pending)` | Frases + Audio; autenticar/autorización antes de persistir bytes; `409 ATTEMPT_PENDING/ATTEMPTS_EXHAUSTED/PHRASE_CLOSED`, `413/415` |
| `GET /practices/:id/anchor-attempts` | → `200 {items:AnchorAttempt[]}` (máximo 15) | Frases; resultado durable frente a eventos perdidos |
| `GET /practices/:id/report` | → `200 Report` publicado | Informe; `409 REPORT_NOT_READY`, `404` ajeno/borrado |
| `GET /history` | → lista paginada de `PracticeSummary` | Historial; solo propias, excluye borradas |
| `GET /comparisons?left=:id&right=:id` | → `200 Comparison` | Historial; ambas propias, `409 INCOMPATIBLE_SESSIONS` |
| `GET /audio/:id` | → bytes con autorización y vigencia revisadas en cada petición/rango | Audio; `404` ajeno/borrado, `410 AUDIO_EXPIRED` propio vencido |
| `GET /references/:id` | → referencia pública del catálogo aprobada | Contenido/Audio; exclusivamente `source=reference`, sin texto procedente de sesiones |
| `DELETE /audio/:id` | → `202 Operation` | Eliminación + Audio; revoca acceso antes de responder |
| `DELETE /practices/:id` | → `202 Operation` | Eliminación; cancela trabajos y revoca antes de responder |
| `DELETE /account` | → `202 Operation` sin datos personales | Eliminación + Identidad; revoca todas las sesiones autenticadas inmediatamente |
| `GET /operations/:id` | → `200 Operation` | Solo propietario; tras borrar cuenta, consulta deja de estar disponible; limpieza sigue internamente |

`PracticeSummary={id,date,topic_id,level,status,report_available,audio_availability}`. El historial consulta el estado vigente del audio; no da por válido un enlace de una proyección antigua. La UI de borrado de cuenta termina en confirmación de solicitud y salida de la cuenta; la evidencia de limpieza física se verifica operativamente.

Las peticiones `DELETE` ya aceptadas se pueden repetir con la misma clave y objetivo propio: devuelven la misma operación, aunque el recurso esté oculto. La deduplicación se resuelve bajo el propietario autenticado original antes de buscar recursos visibles; un identificador ajeno sigue devolviendo `404`. No se conserva autenticación de una cuenta borrada para poder consultar su operación.

## C-04. Audio y tiempo real

Propuesta a confirmar en G0: canal WebSocket en `/api/v1/practices/:id/stream`, autenticado con la misma identidad y ligado a una única instancia de página. Metadatos JSON y frames binarios. Entrada de audio mono PCM signed 16-bit little-endian a 16 kHz, fragmentos de 20 ms; la conversión de navegador y formato de salida TTS deben validarse en el spike de SPEC-00/05. Si no funciona, cambiar ADR-001 y este contrato antes de implementar ambos extremos; no desarrollar dos transportes paralelos.

Negociación `stream.open` `{audio_profile_id,client_instance_id}` → `stream.ready` `{stream_id,audio_profile_id,heartbeat_interval_ms,lease_timeout_ms,max_frame_bytes}`. Rechazo de perfil `UNSUPPORTED_AUDIO_PROFILE` sin iniciar grabación de práctica. El permiso de micrófono puede comprobarse localmente antes; sus muestras de preflight se descartan y nunca se transmiten antes del consentimiento.

Sobre de control: `{v:1,event_id,practice_id,stream_id,seq,occurred_at,type,payload}`. `seq` crece por emisor; `event_id` permite descartar duplicados, `turn_id` y `generation_id` correlacionan audio. No se promete entrega exactamente una vez. Los frames llevan `stream_id,turn_id,generation_id,chunk_seq` mediante cabecera acordada en G0; sin esa cabecera validada no se integra audio real.

| Mensaje | Productor → consumidor | Payload y efecto |
| --- | --- | --- |
| `heartbeat` | Navegador ↔ orquestador | `stream_id`; mantiene lease, no reinicia duración |
| `student.speech_started` | Detector de voz de B → orquestador/tutor | `turn_id,client_offset_ms`; detiene reproducción local inmediatamente, solicita cancelar generación |
| `student.audio` | Navegador → conversación/audio | Frames ordenados por `chunk_seq`; pérdida no se oculta con audio inventado |
| `student.turn_ended` | Navegador/VAD → conversación | `turn_id,last_chunk_seq`; cierra unidad ASR |
| `transcript.updated` | Conversación → navegador | `Turn`; parciales reemplazan por ID, finales se conservan |
| `tutor.audio_started` / `tutor.audio_ended` | Conversación → navegador | `turn_id,generation_id`; aceptar frames solo de generación vigente |
| `tutor.interrupted` | Conversación → navegador/orquestador | `turn_id,generation_id,heard_until_ms`; descartar frames tardíos de esa generación |
| `practice.state_changed` | Orquestador → navegador | `status,state_version,reason_code?,conversation_ends_at?` |
| `anchor.validated` | Frases → navegador | `attempt_id,phrase_id,status,invalid_reason?,attempts_remaining`; el GET durable confirma estado |
| `processing.updated` | Informe → navegador | `stage` en `acoustic,linguistic,report,cleanup`; no porcentaje ficticio |
| `report.ready` | Informe/orquestador → navegador | `report_id,state_version`; solo después del commit de publicación |
| `practice.error` | Orquestador → navegador | `operation_id,code,retryable,resume_state?`; no inicia reintento automático de negocio |

Tras pérdida de canal, solo el mismo documento vivo puede intentar la recuperación manual dentro del lease, con el mismo `client_instance_id` y nonce efímero no persistido del stream. La reconexión de transporte no ejecuta de nuevo operaciones ni reinicia reloj. Una recarga pierde ese contexto: la práctica se termina como incompleta por abandono y se crea otra. El GET de estado no concede reanudación. Si hay huecos en control, se consulta estado durable; no se reproduce audio antiguo para rellenarlos.

## C-05. Interfaces internas, contratos de tareas y evidencia

Llamadas internas dentro del backend reciben `ActorContext` con propietario validado; el proceso de inferencia usa canal privado y credencial de servicio, sin aceptar un `owner_id` arbitrario desde Internet. Todo trabajo incluye `{job_id,practice_id,expected_state_version,deletion_epoch,operation_id,input_refs,deadline_at,attempt}`; resultados duplicados se deduplican por `job_id` y versión. Un input revocado produce `INPUT_REVOKED`, y el resultado tardío se descarta.

| Interfaz | Entrada | Resultado / autoridad |
| --- | --- | --- |
| `Content.snapshot` | `catalog_version` | Temas, objetivos, política, frases y referencias congeladas por sesión |
| `Audio.putTemporary` | contexto, bytes validados, `captured_at`, propósito | `audio_id`; Audio administra bytes, nunca devuelve ruta al navegador |
| `Audio.readForJob` | contexto de trabajo, `audio_id` | Flujo privado si sigue vigente; no prolonga retención |
| `Audio.retainAnchor/Clip` | consentimiento vigente, fuente e intervalo, `captured_at` original | `AudioAsset` autorizado; recorte máximo fijado en ADR-003 |
| `Audio.prepareClipReference` | contexto autorizado, recorte y texto validado del fragmento | `clip_reference` privado, vinculado y con igual vencimiento que el recorte |
| `Audio.finalize/abort` | sesión, versión, epoch | Revocación y limpieza de temporales; ack de limpieza física o error recuperable antes de completar |
| `Evaluator.validateAnchor` | `audio_id,phrase_id,text_en,validity_version` | `valid` o `invalid`, razón acústica/cobertura; errores de pronunciación solos no invalidan |
| `Evaluator.analyze` | trabajo, audio, texto conocido o tokens con confianza, versiones | `PhoneticResult`; no modifica la sesión |
| `Report.build` | transcripción final, cinco intentos válidos, resultados acústicos y manifiesto de cobertura | Borrador interno validable, no visible en historial |
| `Session.publishReport` | informe validado, token de estado y ack de limpieza | Commit de informe público y `completed`; ante epoch distinto descarta |
| `Deletion.request` | actor, `target_type,target_id` | Operación con revocación inmediata y tareas idempotentes por módulo |

`PhoneticResult={id,practice_id,source_audio_id,source_kind,anchor_phrase_id?,evaluator_version,calibration_version,anchor_set_version?,coverage[],evidence[]}`.

`coverage[]={unit_id,start_ms,end_ms,expected_sound?,status:evaluated|not_evaluated,reason?}`. Unidades con ASR dudoso van a `not_evaluated`; ausencia de detección no elimina oportunidades evaluadas. `evidence[]={id,unit_id,start_ms,end_ms,expected_sound,observed_sound?,error_type,confidence,decision_threshold,method}`. Confianza y escala se documentan por versión; puntuaciones agregadas de proveedores no se convierten por supuesto en errores por fonema.

Todas las marcas acústicas son relativas a `source_audio_id`. Un recorte conserva `source_asset_id` e intervalo fuente; la observación usa offsets locales de reproducción además de la referencia de evidencia. El informe retiene el respaldo textual/estructurado permitido al eliminar el temporal, pero no copias encubiertas de sus bytes.

La finalización conserva checkpoints durables: `built → assets_prepared → temporaries_removed → committed`. Antes de borrar temporales quedan guardados el borrador validado, la cobertura y los assets candidatos: cinco anclas válidas, recortes autorizados y sus referencias privadas. Reintentar la limpieza o el commit utiliza ese checkpoint; no intenta volver a evaluar audio ya eliminado. Cancelación, fallo definitivo o borrado eliminan también los assets candidatos de un informe que nunca se publicó.

`Session.publishReport` coordina APIs internas, sin escribir tablas privadas directamente. Si los módulos comparten base, sus operaciones pueden participar en una misma unidad de trabajo. Si los assets/informe se preparan antes en otro almacenamiento, quedan privados: el commit del orquestador fija `completed` y `report_id`, y las lecturas de informe/audio conservado comprueban esa barrera de publicación. Un informe preparado no es visible por existir físicamente. No se exige una transacción distribuida entre base y disco.

## C-06. Informe y comparación

`Report={id,practice_id,language:es,created_at,schema_version,evaluator_version,anchor_set_version,categories,limitations,anchor_summary}`.

- `categories` contiene `pronunciation,grammar,vocabulary`, cada una `{status:observations|no_supported_observations|not_evaluated,observations:[]}`. La ausencia de errores sustentados no se etiqueta como error de procesamiento.
- `Observation={id,category,explanation_es,evidence_refs[],student_quote?,turn_id?,audio_id?,reference_audio_id?,reference_scope?,playback_start_ms?,playback_end_ms?}`. `reference_scope` es `catalog` o `practice` y es obligatorio cuando hay referencia: el cliente usa la ruta pública de catálogo o la privada de audio según ese valor, sin inferirlo del ID. Pronunciación necesita IDs de evidencia acústica; gramática/vocabulario necesitan turno final y cita exacta existente. Si las referencias no validan, no se publica esa observación.
- Para observaciones fonéticas aceptadas de conversación, debe existir recorte autorizado y referencia estadounidense generada/aprobada para el fragmento antes de publicar. La imposibilidad técnica es un fallo de procesamiento recuperable; no se presenta un ejemplo sin soporte como si se hubiera conservado. Las frases usan la referencia del catálogo.
- No incluir nota global, certificación ni una afirmación de mejora pedagógica.
- `anchor_summary[]={phrase_id,sound,evaluated_opportunities,detected_errors,not_evaluated_opportunities}`. Conteos dentro de oportunidades comparables; las unidades no evaluadas nunca cuentan como acierto.
- `Comparison={left_id,right_id,compatible,compatibility_key,sounds[],limitations[]}`. La clave exige misma versión de frases y familia/versión compatible del evaluador y calibración. Hasta disponer de un ADR de equivalencia, solo versiones idénticas son compatibles. Cada fila muestra ambos conteos y denominadores, no una nota global ni mejora garantizada.

## C-07. Plazos y recuperación

Todos los plazos se registran como configuración versionada y se prueban con reloj controlado. G0 define límites de petición y canal para fixtures; G1 mide y cierra valores reales de operación en ADR-003; G3 fija umbrales de aceptación con las mediciones de SPEC-01/12.

| Operación | Custodio del plazo | Al vencer |
| --- | --- | --- |
| HTTP y subida | A/B, ADR-001/003 | Error explícito; repetir transporte con misma clave no duplica intento |
| ASR, tutor, TTS, evaluación e informe | C/B, ADR-002/003 | `recoverable_error` asociado a operación; ofrecer una recuperación manual |
| Lease de canal y ventana de recuperación | A/B, ADR-003 | `incomplete`, revocación de temporales, liberación del cupo tras cancelar tareas |
| Limpieza física y reinicio | A, ADR-003 | Mantener revocación, registrar operación pendiente y reintentar limpieza internamente |

La recuperación manual de una operación es distinta de los dos reintentos por frase acústicamente inválida. Retransmitir bytes confirmados con la misma clave tampoco consume una nueva grabación. Los reintentos automáticos se limitan a transporte o tareas idempotentes de limpieza; no ocultan un fallo de sesión ni repiten conversación/modelos sin la acción manual prevista.

Un incidente conserva su `operation_id` a través del reintento; el fallo de ese reintento es terminal y no crea otro incidente para reiniciar el contador. Un incidente posterior de otra operación puede tener su propia recuperación, siempre dentro de la sesión viva y sus deadlines. Limpiar archivos ya revocados puede seguir en segundo plano después de terminar una práctica incompleta; no vuelve a abrir la sesión ni a habilitar acceso.

## C-08. Fixtures para trabajo paralelo

SPEC-00 publica ejemplos versionados y pruebas de esquema de: dos cuentas, consentimiento aceptado/rechazado/cambiado, sesión por estado, cupo ocupado, intento válido/inválido/pendiente, resultado con evidencia/ausencia/incertidumbre, informe respaldado y cita inválida, audios disponible/vencido/borrado, comparación compatible/incompatible y operación de eliminación pendiente.

Los simuladores son deterministas, se identifican como fixtures en desarrollo y no alimentan métricas ni la demo declarada real. C produce fixtures de evidencia, B de contenido/canal y A de identidad/estado/audio. Cada consumidor prueba contra esos mismos ejemplos. Las preguntas de formato bloquean solo el adaptador afectado hasta G0/G1, no el desarrollo del resto del flujo con fixtures.

## C-09. Perfil de la iteración 1

Vigente durante la iteración 1 del [plan por iteraciones](../ROADMAP.md) (D-14, D-16, D-17 y D-18). C-01 a C-08 describen el contrato completo; este perfil indica qué se omite por ahora y qué se conserva para que la iteración 2 no rompa los DTO.

| Contrato | En la iteración 1 | Llega en |
| --- | --- | --- |
| C-01 autenticación | Sin cookie ni login. El backend usa el usuario base: una cuenta sembrada con `owner_id` constante, que se conserva en la iteración 2 (D-18), y construye `ActorContext` con ella. | Iteración 2 (SPEC-03) |
| C-01 `Idempotency-Key` y CSRF | No se exigen; el cliente no reintenta subidas automáticamente. Se mantiene la validación de `Origin`. | Iteración 2 |
| C-03 consentimiento | Sin texto ni pantalla. El usuario base tiene un `ConsentRecord` sembrado respaldado por el acuerdo escrito del equipo (D-18), que `POST /practices` usa como `consent_id`. `GET /consent-policy` y `POST /consents` no se exponen. | Iteración 2 (SPEC-06) |
| C-03 cuentas, `DELETE` y `/operations` | No se exponen. Cancelar y reintentar devuelven `Operation`, que el cliente sigue con `GET /practices/:id` y `practice.state_changed`. | Iteración 2 (SPEC-03, SPEC-11) |
| C-03 cupo con el usuario base | Si hay una práctica no terminal con el canal abierto, crear otra responde `409 SERVER_BUSY`, también desde otra pestaña o navegador; la anterior solo se termina si su canal ya se cerró. | Se mantiene con cuentas |
| C-04 lease, heartbeat y recuperación de canal | `stream.ready` envía sus campos con valores de configuración, pero cerrar el canal termina la práctica como `incomplete` (D-17). La espera en `recoverable_error` tiene un plazo fijo de configuración; al vencer, la práctica pasa a `incomplete`. | Iteración 2 |
| C-05 `deletion_epoch` y checkpoints | Se omiten. Antes de publicar se comprueba `state_version` y que la práctica no esté cancelada. Orden de finalización: construir y validar el informe → copiar al corpus si el modo está activo → borrar temporales → commit; si falla el commit, se reintenta con el borrador guardado. | Iteración 2 (SPEC-11) |
| C-07 reinicio | Al arrancar, las prácticas no terminales pasan a `incomplete`, se borran sus temporales y se libera el cupo. | Reconciliación completa de ADR-003 en la iteración 2 |
| C-02/C-05 recortes (`conversation_clip`, `clip_reference`) y caducidad | No se generan; `expires_at` queda vacío y las anclas válidas se conservan. | Iteración 2 |
| C-06 observaciones de pronunciación | Solo desde anclas; `limitations` declara que la pronunciación de la conversación no se evaluó. | Iteración 2 |
| C-08 fixtures | Se priorizan los de un propietario; los de dos cuentas, borrado y caducidad pueden esperar. | Iteración 2 |
| Corpus del equipo (D-16) | Con el modo de recolección activo, antes de borrar temporales se copian audio de conversación, transcripciones, informe si existe, evidencia y anclas a `data/corpus/`, también en sesiones canceladas o fallidas; los intentos de anclas inválidos se copian antes de descartarlos. El integrante que hizo la sesión se registra en el manifiesto del corpus mediante la configuración del modo de recolección, no en los DTO. No se sirve por la API ni se sube al repositorio. La copia principal está en el PC de Ivan hasta el cierre del curso. | Continúa para el equipo en la iteración 2; nunca para personas externas |

Se conservan sin cambios: forma de los DTO, estados y `state_version`, cupo hasta `processing`, eventos y perfil de audio del canal, `PhoneticResult` y validación de citas del informe.

El criterio 4 de la [sección 8 de los requisitos](../REQUIREMENTS.md), S06-CA-06, S12-CA-03 y la condición de G2 «con temporales borrados» se verifican sobre el almacenamiento del producto con el modo corpus desactivado; la copia al corpus es la excepción D-16.

Criterios de las specs que dependen de lo omitido. Los demás criterios de las specs de la iteración 1 se verifican sin cambios.

| Criterio | Iteración 1 | Iteración 2 |
| --- | --- | --- |
| SPEC-03 y SPEC-11, todos | — | Completo |
| S04-CA-01 | — | Dos propietarios y clave repetida |
| S04-CA-02 | Otra pestaña o navegador recibe `SERVER_BUSY` y el historial sigue disponible | Otro estudiante |
| S04-CA-04 | Cancelación o cierre del canal | Vencimiento del lease tras recarga |
| S04-CA-05 | Fallo de modelo con un reintento; la ventana es el plazo fijo de configuración | Ventana de ADR-003 |
| S04-CA-06 | Cancelación antes del commit | Borrado antes del commit |
| S04-CA-07 | Versión obsoleta devuelve `STATE_CONFLICT` | Misma clave devuelve el recurso original |
| S05-CA-02 | Captura con el consentimiento sembrado del usuario base | Rechazo sin consentimiento |
| S05-RF-07 / S05-CA-07 | Fallo de ASR, tutor o TTS con reintento manual; el fallo de canal termina la práctica (D-17) | Fallo de canal con recuperación manual |
| S06-CA-01 | — | Completo (texto de consentimiento, D-18) |
| S06-CA-02, S06-CA-04 | Solo el usuario base | Otra cuenta y petición anónima |
| S06-CA-03, S06-CA-05, S06-CA-07 | — | Completo |
| S06-CA-06 | Con el modo corpus desactivado | Completo |
| S07-CA-07 | Fallo del modelo y recuperación manual con el mismo intento | Reenvío con la misma clave |
| S08-CA-02 | — | Conversación libre (P2) |
| S08-CA-06 | Job duplicado | Resultado tras borrado (`deletion_epoch`) |
| S09-CA-02 | Evidencia de anclas y referencia inexistente | Unidad dudosa y recorte de conversación |
| S09-CA-05 | Fallo de limpieza o cancelación antes del commit | Borrado antes del commit |
| S10-CA-01, S10-CA-05 | Un propietario | Dos cuentas |
| S10-CA-03 | — | Completo |
