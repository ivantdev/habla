# SPEC-00 — Base del proyecto y contratos compartidos

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Transversal  
> **RF relacionados:** Derivados de soporte; no amplía el catálogo | **RNF:** RNF-02, RNF-12, RNF-13  
> **RT:** No aplica directamente  
> **Módulo:** Transversal | **Responsable:** A; revisión B y C  
> **Etapa:** E0 | **Iteración:** 1 (semana 1) | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

El repositorio solo contiene requisitos y pautas. Tres personas necesitan una base ejecutable y contratos únicos antes de producir integraciones incompatibles. Esta infraestructura es derivada del MVP; no añade una funcionalidad de usuario.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existen shell web, API, esquemas ejecutables, proxy, tareas ni comandos. Se construirán como salida de esta spec; los nombres lógicos no presuponen carpetas de código aprobadas.

## 3. Historia de usuario

> Como integrante del equipo, quiero ejecutar una base común y simuladores verificables para desarrollar mi módulo sin esperar a que los demás terminen.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro del alcance de la spec

- ADR-001, estructura de código y propietarios acordados en G0.
- Shell web, entrada API/canal, configuración de desarrollo y carga de fixtures.
- Contratos ejecutables y comprobación de compatibilidad para productores y consumidores.

### Fuera del alcance de la spec

- Implementar la lógica de cuentas, audio o modelos de las specs posteriores.
- Fijar umbrales de calidad o prometer latencia sin medición.

### Supuestos acordados

- Confirmados: navegador de escritorio y demo local en equipos del grupo con GPU NVIDIA; nube en la iteración 2. Orientación aceptada el 2026-10-30: FastAPI y React con Vite. Puertos y transporte de la arquitectura son propuestas hasta G0.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S00-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S00-RF-01** (Derivado del entorno de demo) — CUANDO una persona ejecute los comandos documentados en un entorno limpio, EL SISTEMA DEBE iniciar el shell y la API de desarrollo con sus rutas de comprobación accesibles.
- **S00-RF-02** (RNF-02, RNF-13) — EL SISTEMA DEBE validar los DTO de C-01 a C-06 mediante esquemas compartidos versionados que rechacen campos obligatorios ausentes y enums inválidos.
- **S00-RF-03** (Derivado del trabajo paralelo) — MIENTRAS un consumidor use un simulador, EL SISTEMA DEBE devolver respuestas deterministas identificadas como datos de desarrollo.
- **S00-RF-04** (RNF-13) — SI falta una variable requerida del servidor, ENTONCES EL SISTEMA DEBE informar su nombre sin imprimir su valor ni iniciar un servicio parcialmente configurado.
- **S00-RF-05** (RNF-12, RNF-13) — CUANDO el navegador acceda a API y canal a través del origen web, EL SISTEMA DEBE encaminarlos al backend preservando la autenticación y el contrato de negociación.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S00-CA-01** (S00-RF-01) — Dado el entorno de ADR-001 sin dependencias instaladas, Cuando se sigan los comandos del README, Entonces shell y comprobación API funcionan o se informa el prerrequisito faltante sin pasos ocultos.
- [ ] **S00-CA-02** (S00-RF-02) — Dado un fixture válido y otro con estado desconocido, Cuando productor y consumidor ejecuten la prueba de contrato, Entonces aceptan el primero y rechazan el segundo con la misma versión.
- [ ] **S00-CA-03** (S00-RF-03) — Dado el modo fixture, Cuando B y C soliciten la misma sesión, Entonces reciben los mismos IDs y estados y la interfaz muestra que está en simulación.
- [ ] **S00-CA-04** (S00-RF-04) — Dada una configuración incompleta, Cuando se inicie el backend, Entonces falla con el nombre del parámetro y los logs no contienen secretos.
- [ ] **S00-CA-05** (S00-RF-05) — Dado el proxy local, Cuando se consulte API y se abra un stream fixture, Entonces ambos alcanzan el backend; una petición con origen no permitido se rechaza.

## 7. Diseño técnico y datos

**Ubicación y datos:** bootstrap, shell y esquemas; sin tablas de negocio. A posee el arranque, B el shell y C las muestras de inferencia.

**Backend/eventos:** materializar C-01..C-08 en esquemas y fixtures; la sonda operativa no devuelve secretos. Probar la cabecera binaria y el perfil de audio de C-04 con un spike antes de fijarlos. El modo fixture no graba datos reales.

**Frontend:** un router, manejo central de identidad/error y componentes para estados de carga. Cadenas en español y navegación por teclado.

**Proxy/local:** valores propuestos en arquitectura §6; ADR-001 registra los definitivos y después se escriben comandos reales y configuración de ejemplo sin secretos.

**Tecnologías/ADR:** comparar una opción de cliente web con componentes y un backend HTTP con soporte de canal y tareas; seleccionar con compatibilidad del equipo y de la GPU, no por requisitos inexistentes. Todo está propuesto hasta ADR-001.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| B y C → A | Publicar requisitos de shell, evidencia y audio | C-02/C-04/C-05; revisión conjunta | Contrato incompatible bloquea G0, no se integra silenciosamente. |
| A → B/C | Entregar API y esquemas fixture | C-08 | Consumidor mantiene fixtures de la última versión congelada. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S00-D-01** — Se deriva una base común del trabajo de tres personas; diseño propuesto el 2026-10-29.

### Preguntas abiertas

- **S00-P-01 — bloqueante G0:** Elegir stack, estructura, transporte, perfil/cabecera binaria, comandos y puertos; A con B/C, antes de cerrar E0. La sesión web se decide antes de integrar cuentas en la iteración 2 (S03-P-01).
- **S00-P-02 — no bloqueante para fixtures:** Hardware confirmado el 2026-10-30: Ivan (RTX 4090 y RTX 5090) y Nicolás (2× RTX 5060 de 16 GB). Falta verificar VRAM real con `nvidia-smi`, compatibilidad de driver/CUDA/PyTorch con Blackwell y reparto de modelos entre GPU; C, antes de G1.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S00-RF-01 → S00-CA-01 | Integración; registro de instalación limpia. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S00-RF-02 → S00-CA-02 | Contrato; esquemas, fixtures y resultados. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S00-RF-03 → S00-CA-03 | Integración/UI; evidencia del modo fixture. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S00-RF-04 → S00-CA-04 | Integración; salida sanitizada. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S00-RF-05 → S00-CA-05 | Contrato/proxy; prueba de conexión y rechazo. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| RNF-02 | Mantener tarea lenta fixture sin bloquear respuesta de control | Traza de ejecución separada. |
| RNF-12 | Inspección del shell en español y teclado | Capturas y lista de controles. |
| RNF-13 | Configuración y prueba de origen/secretos | Rechazo de origen ajeno, ausencia de credenciales en cliente. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** M: bootstrap, contratos, proxy, spike y automatización mínima.
- **Riesgos:** Un bootstrap demasiado grande retrasa las tres áreas; una cabecera de audio ambigua obliga a rehacer ambos extremos.
- **Consecuencias:** G0 habilita desarrollo paralelo; los fixtures no acreditan funcionalidad del producto.
