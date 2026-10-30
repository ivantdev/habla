# SPEC-12 — Integración, despliegue y aceptación de la demo

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Operación y aceptación  
> **RF relacionados:** RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RF-08, RF-09, RF-10, RF-11, RF-12, RF-13, RF-14, RF-15, RF-16, RF-17, RF-18, RF-19, RF-20 | **RNF:** RNF-01, RNF-02, RNF-03, RNF-04, RNF-05, RNF-06, RNF-07, RNF-08, RNF-09, RNF-10, RNF-11, RNF-12, RNF-13, RNF-14  
> **RT:** RT-01, RT-02, RT-03, RT-04, RT-05, RT-06, RT-07  
> **Módulo:** Operación y aceptación | **Responsable:** A: despliegue; B: recorridos; C: métricas  
> **Etapa:** E3 | **Versión:** 1.0 | **Actualizado:** 2026-10-29

## 1. Contexto y problema

El MVP necesita una demostración integrada que cumpla los ocho criterios finales del catálogo. Pasar tests de módulos o usar fixtures no demuestra voz real, privacidad operativa ni calidad de detección.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existe aplicación desplegada, expediente de pruebas ni evidencia de rendimiento. Esta spec integra entregables existentes; no debe convertirse en el lugar donde recién se implementen permisos, borrado o recuperación.

## 3. Historia de usuario

> Como equipo evaluador, quiero reproducir una demo real y consultar sus mediciones y limitaciones para juzgar el producto con evidencia.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Entorno de demo local reproducible (cifrado si se accede por red), configuración sin secretos y comprobación de dependencias.
- Recorridos completos reales, errores, concurrencia de cupo, borrado y caducidad.
- Resultados congelados, umbrales medidos, manual operativo y expediente de aceptación.

### Fuera de esta iteración

- Escalado multiusuario de voz, producción de alta disponibilidad y despliegue público no solicitado.
- Aprobar metas incumplidas, sustituir modelos por fixtures sin declararlo o añadir funciones de ampliación.

### Supuestos acordados

- Confirmados: escritorio, ejecución local en un equipo del grupo con GPU NVIDIA, una sesión de voz y ocho criterios finales de REQUIREMENTS.md; entrega con presentación tipo *Shark Tank* según D-12. Navegador, equipo de demo y presupuesto no están acordados; la nube queda para V2.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S12-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S12-RF-01** (RT-01, RNF-13) — CUANDO se prepare la demo desde un entorno limpio documentado, EL SISTEMA DEBE iniciar sus componentes reales y declarar versiones, configuración, navegador, red, GPU/memoria y modo de ejecución.
- **S12-RF-02** (RF-01 a RF-15; aceptación 1, 2, 3 y 5) — CUANDO un estudiante complete el recorrido nominal, EL SISTEMA DEBE demostrar cuenta, consentimiento, voz, interrupción, cinco anclas, informe sustentado, historial y comparación entre dos sesiones compatibles.
- **S12-RF-03** (RF-17, RF-18, RF-19; aceptación 4 y 7) — CUANDO se ejecuten casos de muestra inválida, micrófono denegado, servidor ocupado, fallo técnico y recarga, EL SISTEMA DEBE producir los estados y límites de reintento del catálogo sin publicar informe incompleto.
- **S12-RF-04** (RF-16, RF-20, RNF-07, RNF-09; aceptación 6) — CUANDO se verifique el ciclo de vida de datos con dos cuentas y reloj controlado, EL SISTEMA DEBE demostrar aislamiento, borrado de audio/sesión/cuenta y caducidad a 30 días sin borrar indebidamente el texto de informes conservados.
- **S12-RF-05** (RNF-01, RNF-03; RT-02 a RT-07; aceptación 8) — CUANDO se cierre la evaluación final, EL SISTEMA DEBE aportar resultados reales de calidad y rendimiento, umbrales congelados y limitaciones de comparación y generalización.
- **S12-RF-06** (RF-18, RNF-07, RNF-10) — SI una dependencia falla o el servidor reinicia durante la demo, ENTONCES EL SISTEMA DEBE mantener los datos revocados inaccesibles y permitir recuperar operación del servicio sin recrear sesiones terminales ni cupos huérfanos.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S12-CA-01** (S12-RF-01) — Dado un entorno compatible, Cuando otra persona siga el manual, Entonces puede abrir la app en local, o por entrada cifrada si accede por red, y comprobar dependencias; el modo real/fixture es visible y las claves no están en cliente ni repositorio.
- [ ] **S12-CA-02** (S12-RF-02) — Dados dos recorridos reales del mismo usuario, Cuando se completen, Entonces hay evidencia de las etapas, informe sin nota y comparación con denominadores, manteniendo correcciones fuera de charla.
- [ ] **S12-CA-03** (S12-RF-03) — Dados fallos inyectados por separado y un tercer intento inválido, Cuando se recorra cada caso, Entonces se observa recuperación permitida o incompleta, no cuarto intento ni reanudación tras recarga y no queda audio temporal.
- [ ] **S12-CA-04** (S12-RF-04) — Dadas cuentas A/B y audio próximo a caducar, Cuando se borren recursos y avance el reloj, Entonces no hay acceso ajeno o a bytes revocados y se verifica el inventario físico tras reinicio/limpieza.
- [ ] **S12-CA-05** (S12-RF-05) — Dados manifiestos/modelos congelados, Cuando se presente el expediente, Entonces contiene precisión/recall/conteos, muestra/percentiles, comparación acústica/texto y revisión lingüística; una meta no lograda aparece explícitamente.
- [ ] **S12-CA-06** (S12-RF-06) — Dada caída durante grabación, limpieza o publicación, Cuando reinicie el servicio, Entonces la práctica no se reanuda, se reconcilian trabajos/archivos/cupo y puede iniciar otra práctica tras resolver la anterior.

## 7. Diseño técnico y datos

**Ubicación/datos:** configuración de despliegue, migraciones/semillas reales, manual y expediente bajo `docs/`; sin nuevos datos de negocio. Fixtures fuera del dataset de evaluación y del modo real.

**Backend/eventos:** observar `request_id,practice_id,job_id,operation_id`, estados, duración y fallos sin registrar voz, credenciales o contenido personal. Inicialización comprueba versión de esquema, modelos, almacenamiento privado, limpieza programada y acceso real al evaluador. Reinicio reconcilia sesiones/leases y tareas.

**Frontend:** recorrido por navegador de escritorio seleccionado, formularios, micrófono, stream, anclas, informe, historial, comparación y borrado. Verificar teclado, etiquetas y mensajes españoles con contenido inglés. No exigir móvil ni accesibilidad certificada ajena al alcance.

**Proxy/local/demo:** A publica configuración y comandos reales de ADR-001, entrada cifrada si hay acceso por red, upgrade de canal y almacenamiento no público. No desplegar públicamente por el hecho de completar la spec; documentar entorno de demo acordado.

**Tecnologías/ADR:** usar decisiones de G0/G1 y motor congelado de G3. El presupuesto, conexión requerida y memoria real se documentan con las mediciones. Dimensionar una sola sesión; consultas de historial no acaparan el cupo de voz.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| A/B/C → SPEC-00..11 | Integrar contratos y recorridos | C-01..C-08 congelados y criterios de cada spec | Spec no verificada permanece pendiente; no se compensa con fixture. |
| C → SPEC-01/08/09 | Cerrar calidad y rendimiento | Manifiestos, métricas, versiones y corpus | Meta fallida/alternativa inaccesible se declara, sin inventar resultados. |
| A/B → SPEC-06/11 | Demostrar privacidad operativa | Inventario, reloj controlado y tareas | Archivo residual/permiso incorrecto bloquea aceptación correspondiente. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S12-D-01** — Ocho criterios finales en REQUIREMENTS.md, sección 8; el expediente y gates son propuesta de planificación del 2026-10-29.

### Preguntas abiertas

- **S12-P-01 — bloqueante G3:** Definir entorno de demo, conexión/presupuesto, muestra de latencia y límites medidos; A/B/C antes de aceptación.
- **S12-P-02 — bloqueante G3:** Confirmar todos los casos de aceptación y declarar las metas no alcanzadas; A/B/C al cerrar E3.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S12-RF-01 → S12-CA-01 | Despliegue/inspección; manual y registro reproducible. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S12-RF-02 → S12-CA-02 | E2E real; checklist y trazas sin conservar conversación completa. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S12-RF-03 → S12-CA-03 | E2E/fallos; matriz de estados y limpieza. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S12-RF-04 → S12-CA-04 | E2E/operación; acceso, inventario y plazo de depuración. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S12-RF-05 → S12-CA-05 | Evaluación/inspección; expediente reproducible de SPEC-01. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S12-RF-06 → S12-CA-06 | Operación/fallos; reinicio y nueva sesión. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| RF-01, RF-02, RF-03, RF-04, RF-05, RF-10, RF-11, RF-13 | Recorrido de registro y charla real configurada | Aceptación 1 y consentimiento. |
| RF-15, RNF-01 | Interrupción y percentiles reales | Aceptación 2 y trazas. |
| RF-06, RF-07, RF-08, RF-17, RNF-04, RNF-05, RNF-06, RNF-14 | Cinco muestras, duda, evidencia e inválidas | Aceptación 3 y 4. |
| RF-09, RF-12, RF-14, RF-20, RNF-11 | Historial, audios, comparación y ausencia de evidencia | Aceptación 5. |
| RF-16, RNF-07, RNF-09 | Borrado, vencimiento, otra cuenta y residual físico | Aceptación 6. |
| RF-18, RF-19, RNF-02, RNF-10 | Fallos, recarga, cupo e inferencia lenta | Aceptación 7. |
| RNF-03, RT-02, RT-03, RT-04, RT-05, RT-06, RT-07 | Calidad, datos públicos y variantes | Aceptación 8, resultados reales. |
| RNF-08, RNF-12 | Política del tutor e interfaz/teclado | Corpus e inspección UI. |
| RNF-13, RT-01 | Entrada cifrada, secretos y ruta ASR/LLM/TTS | Configuración y prueba real del flujo. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** M de integración si cada módulo entrega sus pruebas; la evaluación experimental larga está en SPEC-01.
- **Riesgos:** Dejar pruebas de borrado/caída o mediciones para el último día; depender de red o proveedor sin alternativa documentada.
- **Consecuencias:** Solo se marcan aprobados criterios efectivamente verificados. Las limitaciones de datos públicos y metas no alcanzadas acompañan la demo.
