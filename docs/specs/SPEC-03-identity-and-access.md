# SPEC-03 — Cuentas, autenticación y acceso propio

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Identidad  
> **RF relacionados:** RF-11 | **RNF:** RNF-09, RNF-12, RNF-13  
> **RT:** No aplica directamente  
> **Módulo:** Identidad | **Responsable:** A; B integra formularios  
> **Etapa:** E3 | **Iteración:** 2 (P0 para el pitch); la iteración 1 usa el propietario local de C-09 | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

Cada estudiante necesita una cuenta para consultar su historial sin acceder a sesiones o audios ajenos. El catálogo incluye correo/contraseña y excluye verificación y recuperación por correo en la demo.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existen cuentas, credenciales, middleware ni pantallas de acceso. La implementación debe ofrecer una identidad común a API, canal y operaciones internas.

## 3. Historia de usuario

> Como estudiante, quiero registrarme, iniciar y cerrar sesión para usar mi historial con acceso exclusivo a mis datos.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Registro, acceso, consulta de identidad y cierre de sesión.
- Contrato de autorización por propietario para todos los módulos.
- Formularios accesibles y bloqueo de cuenta usado por eliminación.

### Fuera de esta iteración

- Recuperación/verificación por correo, login social, roles administrativos y compartir sesiones.
- Implementar borrado completo de datos, que pertenece a SPEC-11.

### Supuestos acordados

- Confirmados: correo y contraseña, hash adaptativo con sal y acceso del propietario. Política de contraseña, normalización de correo y duración de sesión son decisiones de ADR-001.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S03-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S03-RF-01** (RF-11, RNF-09) — CUANDO un estudiante envíe correo disponible y contraseña que cumplan la política publicada, EL SISTEMA DEBE crear una cuenta y almacenar únicamente el hash adaptativo con sal de la contraseña.
- **S03-RF-02** (RF-11) — SI el correo no cumple la validación, está ocupado o la contraseña incumple la política, ENTONCES EL SISTEMA DEBE rechazar el registro sin crear una cuenta parcial.
- **S03-RF-03** (RF-11) — CUANDO se presenten credenciales válidas de una cuenta activa, EL SISTEMA DEBE establecer una sesión autenticada identificable por el servidor.
- **S03-RF-04** (RF-11, RNF-09) — CUANDO el estudiante cierre sesión, EL SISTEMA DEBE invalidar su sesión autenticada en servidor y cerrar o revocar los canales vinculados a ella.
- **S03-RF-05** (RNF-09) — SI una petición carece de identidad válida o solicita un recurso ajeno, ENTONCES EL SISTEMA DEBE denegar el acceso según C-01 sin revelar el recurso protegido.
- **S03-RF-06** (RNF-13) — MIENTRAS la aplicación se use a través de la red de la demo, EL SISTEMA DEBE proteger credenciales y sesión en tránsito y mantener los secretos de proveedores fuera del cliente.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S03-CA-01** (S03-RF-01) — Dados datos válidos, Cuando se registre la cuenta, Entonces puede autenticarse y la inspección del almacenamiento y logs no encuentra contraseña en claro.
- [ ] **S03-CA-02** (S03-RF-02) — Dados correo malformado, correo repetido y contraseña inválida, Cuando se envíen por separado, Entonces se obtienen los errores definidos y el conteo de cuentas no aumenta.
- [ ] **S03-CA-03** (S03-RF-03) — Dada una cuenta activa, Cuando ingrese y consulte /auth/me, Entonces recibe su identidad; con contraseña errónea recibe INVALID_CREDENTIALS sin cookie válida.
- [ ] **S03-CA-04** (S03-RF-04) — Dada una cookie capturada antes de salir y un canal abierto, Cuando se cierre sesión, Entonces reutilizar la cookie falla y el canal ya no recibe datos privados.
- [ ] **S03-CA-05** (S03-RF-05) — Dadas cuentas A y B y un audio de A, Cuando B o una petición anónima intente leerlo, modificarlo o eliminarlo por ID, Entonces recibe 404 o 401 y el dato no cambia.
- [ ] **S03-CA-06** (S03-RF-06) — Dada la demo configurada, Cuando se inspeccionen respuestas, cookies, bundle y conexión, Entonces se usa entrada cifrada cuando el acceso es por red y no aparecen claves del servidor.

## 7. Diseño técnico y datos

**Datos:** Identidad administra cuenta y sesión autenticada. Otros módulos guardan `owner_id` opaco, nunca leen hashes ni alteran credenciales. El middleware entrega `ActorContext` y un verificador común para peticiones/canal.

**Backend:** operaciones de cuentas y autenticación en C-03; cookie, CSRF y origen según C-01. Registro no inicia grabación. Transacción de unicidad de correo, sesión servidor revocable y errores sanitizados. El cierre de una sesión web activa inicia abandono/cancelación de práctica conforme SPEC-04.

**Frontend:** `/registro`, `/ingresar` y estado de cuenta dentro del shell de B. Etiquetas, validación asociada al campo, foco en primer error y envío por teclado; no mostrar funciones excluidas.

**Eventos:** evento interno de revocación a orquestador/canal, identificado por sesión web, sin difundir correo ni contraseña.

**Proxy/local:** mismo origen `/api/v1`, sin proveedor de identidad externo obligatorio.

**Tecnologías/ADR:** librería mantenida de hash adaptativo y almacenamiento de sesión son selección de ADR-001; no implementar criptografía propia. La política concreta se acuerda antes de escribir validadores en ambos extremos.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| Cliente/B → Identidad | Autenticar y conocer estado | C-01/C-03 | 401 provoca salida del estado privado, sin bucle infinito. |
| SPEC-04/06/09/10/11 → Identidad | Autorizar acceso a datos | ActorContext y verificador por propietario | Cuenta revocada impide nuevas operaciones/publicación. |
| SPEC-11 → Identidad | Bloquear y revocar toda la cuenta | Operación interna idempotente por account_id | El fallo de limpieza posterior no vuelve a habilitar acceso. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S03-D-01** — Alcance de cuentas en RF-11/RNF-09; cookie de sesión es propuesta de diseño del 2026-10-29 hasta G0.

### Preguntas abiertas

- **S03-P-01 — bloqueante para integrar cuentas (iteración 2):** Elegir hash, política de contraseña/correo, expiración, CSRF y formato de sesión; A, en ADR-001 o una adenda antes de integrar formularios reales. No bloquea G0: la iteración 1 usa el propietario local de C-09.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S03-RF-01 → S03-CA-01 | Integración/inspección; cuenta y esquema de credenciales. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S03-RF-02 → S03-CA-02 | Integración/UI; casos de validación y unicidad concurrente. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S03-RF-03 → S03-CA-03 | Integración; login, consulta y rechazo. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S03-RF-04 → S03-CA-04 | Integración/canal; revocación efectiva. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S03-RF-05 → S03-CA-05 | Contrato transversal; matriz de operaciones por recurso. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S03-RF-06 → S03-CA-06 | Despliegue/inspección; configuración y artefacto cliente. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| RF-11 | Registro, duplicados, login, logout y cookie anterior | Suite de integración y recorrido UI. |
| RNF-09 | Matriz anónimo/propietario/otra cuenta para cada recurso | Rechazos sin datos ni mutaciones. |
| RNF-12 | Formularios en español accesibles por teclado | Inspección de interfaz. |
| RNF-13 | Tránsito, cookies y secretos del cliente | Configuración de entrada y revisión del bundle. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** M: persistencia, middleware y formularios; no recuperar contraseñas en esta fase.
- **Riesgos:** Normalización divergente, cookies aceptadas tras logout o autorización solo en UI comprometen los demás módulos.
- **Consecuencias:** La cuenta no certifica identidad por correo; el contrato de permisos es obligatorio para cada consumidor.
