# Arquitectura del MVP de ¡Habla!

**Estado** · Diseño del MVP y componentes implementados del perfil C-09. Actualizado el 2026-11-20. **Custodio** · Persona A, con revisión de B y C.

Este documento y [CONTRACTS.md](CONTRACTS.md) definen la base compartida de las [specs](../specs/README.md). El diseño completo sigue sujeto a los gates de integración. Los requisitos confirmados en [REQUIREMENTS.md](../REQUIREMENTS.md) conservan su autoridad sobre el alcance. La sección 9 y el [diagrama editable](COMPONENTS.mmd) describen la implementación local que existe actualmente, con sus adaptadores simulados.

## 1. Límites y estilo propuestos

Un cliente web y un backend modular, con ejecución de modelos en tareas separadas de la atención HTTP y del audio en tiempo real. Se propone una sola unidad de despliegue de aplicación y un proceso de inferencia cuando lo exija el aislamiento de GPU; los módulos lógicos no implican microservicios, bases separadas ni un broker.

```mermaid
flowchart LR
  U[Navegador] --> G[Entrada web y API]
  G --> I[Identidad]
  G --> O[Orquestador de sesión]
  G --> H[Historial y consultas]
  O --> V[Conversación: ASR, tutor, TTS]
  O --> F[Frases ancla]
  O --> R[Informe]
  V --> M[Audio temporal y conservado]
  F --> M
  M --> P[Evaluación fonética]
  P --> R
  V --> R
  H --> R
  H --> M
  X[Eliminación] --> O
  X --> M
  X --> H
```

Las flechas representan colaboración mediante interfaces; no conceden acceso directo al almacenamiento privado de otro módulo. El flujo acústico debe continuar aunque haya evaluación pendiente. Cada implementación de almacenamiento y cola podrá reemplazarse sin cambiar los DTO compartidos.

## 2. Autoridad y límites de escritura

| Módulo | Spec | Responsable | Datos y decisiones que posee |
| --- | --- | --- | --- |
| Base, shell y contratos | SPEC-00 | A; B/C revisan | Configuración compartida, registro de rutas y contratos; no datos de negocio |
| Experimentos | SPEC-01 | C | Manifiestos de datos, particiones, calibraciones, resultados y ADR del evaluador |
| Contenido | SPEC-02 | B; C revisa | Niveles, temas, objetivos, cinco frases y referencias estadounidenses versionadas |
| Identidad | SPEC-03 | A | Cuenta, hash, sesión autenticada, autorización y bloqueo de cuenta |
| Orquestación | SPEC-04 | A | Estado y versión de sesión de práctica, reloj, ocupación, operación recuperable |
| Conversación | SPEC-05 | B | Turnos, transcripción, generación y reproducción del tutor |
| Audio y consentimiento | SPEC-06 | A; B/C consumen | Consentimiento, metadatos y bytes, vencimiento, accesibilidad y limpieza |
| Frases ancla | SPEC-07 | B | Intentos, orden, resultado de validez; consulta el catálogo |
| Evaluación fonética | SPEC-08 | C | Evidencia acústica, cobertura y versión del evaluador; no decide estado global |
| Informe | SPEC-09 | C | Informe final, observaciones, referencias de evidencia y publicación |
| Historial y comparación | SPEC-10 | A | Proyección de lectura y comparación; consulta las fuentes autoritativas |
| Eliminación | SPEC-11 | B | Operación de borrado y coordinación; cada módulo elimina sus propios datos |
| Aceptación y operación | SPEC-12 | A/B/C | Configuración de demo, mediciones y expediente de aceptación |

Compartir una base de datos es válido; las tablas siguen teniendo un solo escritor lógico. Las consultas entre módulos pasan por interfaces o proyecciones identificadas. No introducir escritura cruzada desde el frontend ni desde el worker.

## 3. Invariantes y estados

Estado global de práctica, autoridad de SPEC-04:

| Estado | Entrada | Salida permitida y condición |
| --- | --- | --- |
| `ready` | Creación con identidad, configuración, consentimiento y cupo válidos | `conversation` al iniciar audio; `incomplete` al cancelar/abandonar |
| `conversation` | `conversation_started_at` fijado una sola vez | `anchors` al vencer la duración; `recoverable_error` ante fallo recuperable; `incomplete` por cancelación |
| `anchors` | Cierre de charla; no nuevos turnos conversacionales | `processing` tras cinco muestras válidas; `recoverable_error`; `incomplete` al agotar intentos/cancelar |
| `processing` | Snapshot de cinco muestras válidas y charla cerrada | `completed` al publicar informe válido; `recoverable_error`; `incomplete` por cancelación |
| `recoverable_error` | Se guarda `resume_state`, operación e intentos de recuperación | Estado anterior tras el único reintento manual exitoso; `incomplete` si falla, vence el plazo o se cancela |
| `completed` | Informe publicado y temporales inaccesibles, con limpieza física confirmada antes de finalizar la operación | Solo eliminación; no reanuda grabación |
| `incomplete` | Motivo terminal registrado y temporales revocados | Solo eliminación; no puede publicar informe |

El cupo se conserva desde `ready` hasta `processing`, incluyendo error recuperable, para evitar solapamiento de trabajos GPU y cierre (decidido el 2026-10-30, S04-P-01); el historial permanece disponible.

- Una transición compara `state_version`; duplicados no repiten efectos. La sesión y el cupo se actualizan de forma atómica o mediante una operación durable equivalente.
- El reloj de conversación es del servidor y monotónico para el cálculo; se guardan instantes UTC para presentación. Pausas y errores consumen tiempo de charla. Recuperar no reinicia el reloj; si ya venció, se cierra hacia `anchors`.
- Una recarga o nuevo canal no reanuda una práctica anterior. El backend detecta abandono por lease/heartbeat; antes de crear otra práctica del mismo usuario termina y limpia la anterior solo si fue abandonada. Si la anterior sigue activa, la creación responde `409 SERVER_BUSY`. Los plazos son decisiones de G0/G1 y no latencias prometidas del producto. En la iteración 1, cerrar el canal termina la práctica como incompleta (D-17, C-09).
- Cancelar o eliminar gana frente a una publicación tardía: un trabajo solo publica si coinciden propietario vigente, `state_version`, `deletion_epoch` y estado permitido.
- Borrar audio tras un informe conserva el texto del informe. Borrar sesión/cuenta elimina también sus textos. La revocación de acceso precede a la limpieza física.
- Cero observaciones no significa pronunciación perfecta. Evidencia ausente o dudosa se identifica como no evaluada.

## 4. Datos y relaciones lógicas

```mermaid
erDiagram
  Account ||--o{ PracticeSession : posee
  Account ||--o{ ConsentRecord : acepta
  PracticeSession ||--o{ Turn : contiene
  PracticeSession ||--o{ AnchorAttempt : contiene
  PracticeSession ||--o{ AudioAsset : vincula
  PracticeSession ||--o| Report : publica
  AnchorSet ||--|{ AnchorPhrase : define
  AnchorPhrase ||--o{ AnchorAttempt : identifica
  AudioAsset ||--o{ PhoneticEvidence : sustenta
  Report ||--o{ Observation : contiene
```

Esquema conceptual; no obliga a un ORM. `Report` solo existe públicamente si está publicado; resultados intermedios no son informes del historial. Las referencias generadas desde un recorte personal también son privadas y comparten su ciclo de vida; solo las referencias del catálogo son públicas. El registro de eliminación podrá sobrevivir temporalmente sin correo, texto, audio ni identificadores de proveedores, solo para terminar la limpieza; su política se fija en SPEC-11.

## 5. Frontend y propiedad de pantallas

B integra navegación y componentes compartidos; A entrega formularios de cuenta mediante las interfaces de B, y B implementa la vista de informe a partir del DTO de C, que la revisa. Rutas propuestas: `/registro`, `/ingresar`, `/practica`, `/sesiones`, `/sesiones/:id`, `/comparar`, `/cuenta`. La ruta de práctica muestra configuración, permiso de micrófono, consentimiento, conversación, frases, espera y fallo como estados de un mismo flujo.

No se permite que varios módulos instalen routers o manejadores de autenticación distintos. Las cadenas visibles y errores explicables están en español; el texto de tutor y frases en inglés. Controles con etiquetas, foco visible, operación por teclado y estados anunciables; las comprobaciones concretas pertenecen a cada spec.

## 6. Entrada, proxy y configuración

Propuesta de G0: origen único; desarrollo web `127.0.0.1:3000`, backend `127.0.0.1:8000`, canal bajo `/api/v1/practices/:id/stream` y API bajo `/api/v1`. El servidor web reenvía esas rutas al backend, con soporte de actualización de canal. La inferencia, si usa otro proceso, solo es interna y su puerto se declara en configuración de servidor.

Son valores propuestos, todavía no instrucciones ejecutables. SPEC-00 confirma puertos, comandos, variables y transporte en ADR-001 antes de implementar clientes reales. El MVP se ejecuta en local (D-13): en `localhost` el navegador permite el micrófono sin HTTPS. Si se accede desde otro equipo por red, entrada HTTPS y canal cifrado. El despliegue en la nube queda para la iteración 2. Credenciales de servicios solo en servidor. No registrar contraseñas, cookies, textos completos ni audio en telemetría de operación.

## 7. Decisiones y límites de tecnología

| ADR a producir | Custodio | Debe resolver | Gate |
| --- | --- | --- | --- |
| ADR-001 | A con B/C | Lenguajes, web/backend, persistencia, canal, codificación de audio, puertos, scripts, autenticación y ejecución de tareas | G0 |
| ADR-002 | C con A/B | Evaluador, evidencia disponible, costos, licencias, confianza, validez y versión compatible | G1 para usar modelo real; selección final G3 |
| ADR-003 | A con B/C | Lease/heartbeat, deadlines, límites de carga, limpieza física y comportamiento ante reinicio | G1: deadlines y límites de carga; iteración 2: lease/heartbeat, recortes, limpieza física y reinicio |
| ADR-004 | B con C | Catálogo de frases/referencias, guía del tutor, parte de TTS no escuchada | G1 |

Opciones a estudiar: web con componentes y backend HTTP; persistencia relacional; almacenamiento privado local para la demo; tareas internas con cola acotada. El 2026-10-30 el equipo aceptó como orientación FastAPI (Python) en el backend y React con Vite en el frontend; ADR-001 la formaliza. No se selecciona proveedor por insinuación. Pesos abiertos y las GPU locales del grupo (RTX 4090/5090 y 2× RTX 5060 de 16 GB) son orientación del catálogo; compatibilidad, memoria y acceso deben medirse. No hacen falta servicios distribuidos para cumplir estos contratos.

La base local C-09 ya implementa React/Vite, FastAPI y SQLite. Sus decisiones de operación están en [ADR-001](ADR-001-local-development.md) y [ADR-003](ADR-003-fixture-operation.md). El diagrama de la sección 1 conserva el diseño completo previsto para el MVP.

## 8. Protocolo para modificar contratos

Quien posee un contrato propone el cambio y actualiza las specs afectadas. Sus consumidores B/C/A revisan ejemplos y pruebas de contrato antes de integrarlo. Durante una etapa se agregan campos opcionales compatibles; renombrar, quitar campos o cambiar semántica requiere nueva versión y migración acordada. Los archivos compartidos tienen un custodio; los demás aportan cambios en revisiones pequeñas. El flujo de trabajo está en [el plan de specs](../specs/README.md).

## 9. Componentes y conectores implementados

El sistema local ejecuta el servidor web de desarrollo y un proceso FastAPI. Los componentes dentro del backend se comunican mediante llamadas Python y tareas asíncronas del mismo proceso. El flujo de conversación, la validez acústica, la evaluación y la generación inicial de observaciones usan adaptadores de simulación. El diagrama se entrega también en [SVG](COMPONENTS.svg) y [PNG](COMPONENTS.png).

```mermaid
flowchart LR
  subgraph browser["Navegador"]
    direction LR
    UI["Frontend React<br/>Pantallas de HABLA"]
    CLIENT["Cliente HTTP<br/>JSON Schema v1"]
    STREAM["Canal de audio<br/>Cliente WebSocket"]
    PLAYER["Reproductor del navegador<br/>Muestras y referencias"]
    UI --> CLIENT
    UI --> STREAM
    UI --> PLAYER
  end
  VITE["Vite · puerto 3000<br/>Assets y proxy"]
  CLIENT <-->|"HTTP /api/v1<br/>JSON y multipart"| VITE
  STREAM <-->|"WebSocket<br/>Eventos JSON y PCM"| VITE
  PLAYER <-->|"HTTP GET<br/>Audio WAV"| VITE
  subgraph backend["FastAPI · 127.0.0.1:8000"]
    API["Entrada FastAPI<br/>DTO · origen · acceso"]
    ID["Identidad base<br/>Usuario y consentimiento"]
    ORCH["Orquestador<br/>Estados · reloj · cupo"]
    SIM["Adaptadores simulados<br/>ASR · tutor · TTS<br/>Validez · evaluación · informe"]
    REPORT["Validador de informe<br/>Citas y evidencia"]
    HISTORY["Historial y comparación<br/>Conteos por sonido"]
    AUDIO["Gestor de audio<br/>Acceso y limpieza"]
    STORE["Persistencia<br/>Estados y registros"]
    API -->|"Al iniciar"| ID
    API --> ORCH
    API --> HISTORY
    API --> AUDIO
    ORCH <-->|"Llamadas asíncronas y resultados"| SIM
    ORCH -->|"Borrador y evidencia"| REPORT
    ORCH --> AUDIO
    ORCH --> STORE
    HISTORY --> STORE
    HISTORY --> AUDIO
  end
  VITE <--> API
  DB[("SQLite<br/>data/habla.sqlite3")]
  FILES[("Archivos de audio<br/>data/audio/")]
  CORPUS[("Corpus opcional del equipo<br/>data/corpus/")]
  STORE <-->|"SQL y transacciones"| DB
  ID -->|"Siembra de identidad"| DB
  AUDIO <-->|"Metadatos de audio"| DB
  AUDIO <-->|"Lectura, escritura y limpieza"| FILES
  ORCH -->|"Copia opcional<br/>antes de limpiar"| CORPUS
  classDef implemented fill:#f0f5ea,stroke:#699254,color:#243d31
  classDef simulated fill:#fff1df,stroke:#c29961,color:#694b25
  classDef storage fill:#eef2f7,stroke:#8ca2b7,color:#34495c
  class UI,CLIENT,STREAM,PLAYER,VITE,API,ID,ORCH,REPORT,HISTORY,AUDIO,STORE implemented
  class SIM simulated
  class DB,FILES,CORPUS storage
  style browser fill:#f6f9f2,stroke:#d8e4ce,color:#243d31
  style backend fill:#fafcf8,stroke:#cbdac0,color:#243d31
```

El canal `/api/v1/practices/:id/stream` transporta eventos y audio de la conversación. Los reproductores usan HTTP GET a `/api/v1/audio/:id` para muestras y a `/api/v1/references/:id` para referencias. El orquestador recoge el borrador y la evidencia de los adaptadores, llama al validador y guarda el informe validado antes de la limpieza y la publicación.

### Correspondencia con el código

| Componente | Archivo principal | Responsabilidad |
| --- | --- | --- |
| Interfaz React | [main.jsx](../../web/src/main.jsx), [Practice.jsx](../../web/src/Practice.jsx), [History.jsx](../../web/src/History.jsx) | Navegación, selección, conversación, anclas, informe, historial y comparación. |
| Cliente HTTP y esquemas | [api.js](../../web/src/api.js), [contract.js](../../web/src/contract.js), [v1.json](../../contracts/v1.json) | Peticiones al mismo origen y comprobación del contrato compartido. |
| Canal del navegador | [fixture-stream.js](../../web/src/fixture-stream.js) | Eventos de control, frames sintéticos y reproducción de la generación vigente. |
| Reproductores de WAV | [Practice.jsx](../../web/src/Practice.jsx), [History.jsx](../../web/src/History.jsx) | Lectura HTTP de las muestras guardadas y las referencias del catálogo. |
| Proxy de desarrollo | [vite.config.js](../../vite.config.js) | Sirve la web y reenvía HTTP y WebSocket a FastAPI. |
| Entrada y canal de servidor | [app.py](../../habla/app.py), [ws.py](../../habla/ws.py), [channel.py](../../habla/channel.py) | Rutas, negociación y validación de origen, DTO, eventos y cabecera binaria. |
| Identidad base | [identity.py](../../habla/identity.py) | Actor y consentimiento sembrados de D-18. |
| Orquestación | [orchestration.py](../../habla/orchestration.py) | Máquina de estados, reloj, cupo, tareas, reintento, publicación y recuperación tras reinicio. |
| Simuladores | [simulators.py](../../habla/simulators.py), [fixtures.py](../../habla/fixtures.py) | Salidas deterministas, catálogo, referencias sintéticas y fallos controlados. |
| Barrera de informe | [report_validation.py](../../habla/report_validation.py) | Comprueba citas exactas del estudiante y evidencia acústica antes del commit. |
| Historial y comparación | [history.py](../../habla/history.py) | Listados paginados y comparación de versiones compatibles con denominadores explícitos. |
| Audio y corpus | [audio.py](../../habla/audio.py) | Gestión de bytes, metadatos, rangos, limpieza y copia interna opcional. |
| Persistencia | [storage.py](../../habla/storage.py) | Transacciones de estado, reserva única y almacenamiento de turnos, intentos y borradores. |

### Integraciones pendientes

Los adaptadores reales de ASR, tutor, TTS y evaluación se conectan donde hoy actúa [simulators.py](../../habla/simulators.py), respetando C-04/C-05 y los plazos que cierre el equipo en G1. Cuentas y consentimiento para personas externas, recuperación del canal, caducidad, borrado y despliegue siguen el alcance de la iteración 2 del [roadmap](../ROADMAP.md).
