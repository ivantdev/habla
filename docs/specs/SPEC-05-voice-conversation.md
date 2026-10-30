# SPEC-05 — Conversación, transcripción e interrupciones

> **Estado:** Borrador | **Prioridad:** P1 | **Dominio:** Experiencia de voz  
> **RF relacionados:** RF-02, RF-03, RF-04, RF-05, RF-15, RF-19 | **RNF:** RNF-01, RNF-02, RNF-08, RNF-12, RNF-13  
> **RT:** RT-01  
> **Módulo:** Experiencia de voz | **Responsable:** B; C asesora modelos y A canal  
> **Etapa:** E1–E2 | **Iteración:** 1 | **Versión:** 1.0 | **Actualizado:** 2026-10-30

## 1. Contexto y problema

El estudiante debe conversar con naturalidad y recibir las correcciones después. La transcripción apoya la conversación, mientras la evaluación acústica se realiza en otra ruta sin bloquearla.

Fuente: [catálogo de requisitos](../REQUIREMENTS.md). Diseño compartido: [arquitectura](../architecture/ARCHITECTURE.md) y [contratos](../architecture/CONTRACTS.md). [Plan, etapas y reglas de trabajo](README.md).

## 2. Estado del sistema y brecha

No existe captura web, detector de habla, ASR, tutor ni TTS. La spec incluye integración completa de estos adaptadores; no supone que mencionar Whisper equivalga a tenerlo instalado.

## 3. Historia de usuario

> Como estudiante, quiero hablar, escuchar al tutor e interrumpirlo para practicar una conversación fluida sin correcciones durante la charla.

Actores secundarios: integrantes A/B/C y módulos consumidores según §8. Las operaciones sobre datos personales requieren propietario autenticado; las tareas internas actúan con contexto autorizado de C-05.

## 4. Alcance

### Dentro de esta iteración

- Preflight de micrófono, captura, turnos, ASR, tutor contextual y TTS.
- Transcripción parcial/final, interrupción, descarte de salida tardía y trazas de latencia.
- Adaptadores con fixtures antes de conectar modelos reales.

### Fuera de esta iteración

- Evaluar errores de pronunciación mediante ASR o corregir durante la charla.
- Continuar conversación después del vencimiento y reanudar tras recarga.

### Supuestos acordados

- Confirmados: inglés, transcripción sin marcas, tutor que admite interrupciones y aclaraciones conversacionales. Perfil de audio y política de texto no escuchado son propuestas de G0/G1.

Las propuestas se revisan en los gates definidos por el plan.

## 5. Requisitos funcionales

IDs `S05-RF-*` son descomposiciones locales estables, no renumeraciones de `RF-*` del catálogo. Redacción EARS según la convención del plan.

- **S05-RF-01** (RF-19) — CUANDO el estudiante compruebe el micrófono, EL SISTEMA DEBE mostrar su disponibilidad y permitir repetir la comprobación si se deniega sin iniciar grabación de práctica.
- **S05-RF-02** (RF-02) — MIENTRAS la práctica esté en conversation con consentimiento vigente y canal autorizado, EL SISTEMA DEBE enviar la voz del estudiante al procesamiento de turnos.
- **S05-RF-03** (RF-03, RF-05, RT-01) — CUANDO se cierre una intervención comprensible, EL SISTEMA DEBE generar una respuesta hablada en inglés acorde al tema y nivel sin correcciones de evaluación.
- **S05-RF-04** (RF-04) — CUANDO se reciban transcripciones parciales o finales, EL SISTEMA DEBE mostrarlas por turno y orden sin marcas de errores ni duplicados.
- **S05-RF-05** (RF-15) — CUANDO el estudiante comience a hablar mientras suena el tutor, EL SISTEMA DEBE detener la reproducción, cancelar la generación activa y capturar la nueva intervención descartando frames tardíos de la generación anterior.
- **S05-RF-06** (RNF-02) — MIENTRAS exista análisis fonético pendiente, EL SISTEMA DEBE poder continuar los turnos conversacionales sin esperar su resultado.
- **S05-RF-07** (RF-03; contrato con RF-18) — SI falla ASR, tutor, TTS o canal, ENTONCES EL SISTEMA DEBE notificar la operación fallida al orquestador y detener la salida inconsistente sin reproducir una respuesta inventada.

## 6. Criterios de aceptación

Todos pendientes; escenarios propuestos para implementación y verificación. Cada criterio indica su requisito local.

- [ ] **S05-CA-01** (S05-RF-01) — Dado permiso denegado o dispositivo ausente, Cuando se haga preflight, Entonces aparecen instrucciones en español y botón de comprobar otra vez; no se envía audio al backend.
- [ ] **S05-CA-02** (S05-RF-02) — Dada práctica autorizada, Cuando el estudiante hable, Entonces se recibe un turno asociado a su sesión; sin consentimiento o fuera de conversation no se persiste ni procesa el flujo conversacional.
- [ ] **S05-CA-03** (S05-RF-03) — Dados turnos comprensible e incomprensible, Cuando responda el tutor, Entonces sigue el tema/nivel o pide aclaración para conversar y no solicita repetir por un error de pronunciación.
- [ ] **S05-CA-04** (S05-RF-04) — Dados parciales repetidos y un final, Cuando lleguen a la UI, Entonces una intervención se actualiza en su lugar y el final queda una sola vez sin evaluación visible.
- [ ] **S05-CA-05** (S05-RF-05) — Dado tutor reproduciéndose y audio tardío en cola, Cuando comience voz del estudiante, Entonces cesa la salida anterior, se captura el nuevo turno y no reaparece la voz cancelada.
- [ ] **S05-CA-06** (S05-RF-06) — Dado un evaluador deliberadamente lento, Cuando se complete un nuevo turno de voz, Entonces ASR/tutor/TTS continúan sin esperar y la cola de evaluación permanece acotada según ADR-003.
- [ ] **S05-CA-07** (S05-RF-07) — Dado fallo en cada adaptador, Cuando se produzca, Entonces se emite practice.error mediante el orquestador y solo la recuperación manual de SPEC-04 permite continuar.

## 7. Diseño técnico y datos

**Datos:** Conversación posee Turn y el estado de generación TTS, con IDs, tiempos, texto final y parte efectivamente escuchada. Audio posee bytes. Solo textos finales coherentes alimentan el informe; marcar la parte del tutor no escuchada evita continuar desde una frase que el estudiante nunca oyó.

**Backend/tiempo real:** C-04 y C-05; la ruta ASR→tutor→TTS usa snapshot de contenido. Detección local detiene reproducción sin viaje de red y comunica cancelación al servidor; VAD y umbral de falsa interrupción se calibran. El mensaje final de cada turno delimita audio para evaluación.

**Frontend:** pantalla `/practica`: preflight, micrófono activo, tutor hablando, transcripción, contador y cancelar. Etiquetas «Comprobar micrófono», «Cancelar práctica» y estados anunciables. Evitar realimentación del altavoz; documentar condiciones y uso de auriculares en la demo si la prueba lo requiere.

**Proxy/local:** stream autenticado del origen único; negociar perfil/cabecera antes de enviar bytes. No tokens por query ni claves de modelos en navegador.

**Tecnologías/ADR:** ASR (Whisper es candidato), modelo de lenguaje, TTS y VAD abiertos si resultan viables; acceso a GPU, memoria y soporte real se prueban. ADR-001 fija transporte; ADR-004 fija qué parte escuchada entra al contexto del siguiente turno.

## 8. Dependencias y contratos de integración

| Dependencia/consumidor | Propósito | Contrato o dato intercambiado | Modo de fallo |
| --- | --- | --- | --- |
| B → SPEC-02/03/04/06 | Obtener contexto, permisos y fuente de audio | C-02/C-04/C-05; contexto de usuario | Sin precondiciones no transmitir/persistir audio. |
| Conversación → SPEC-08/09 | Entregar audio por referencia y texto con confianza | Turn final, audio_id y offsets | ASR dudoso se marca; no se inventa confianza. |
| SPEC-04 → Conversación | Cerrar al vencer/cancelar | state_version y cancelación de generation_id | No abrir turnos ni reproducir frames obsoletos. |

Autenticación interna, plazos, reintentos y duplicados: C-01, C-04, C-05 y C-07. Datos compartidos mediante DTO o interfaces, sin leer/escribir almacenamiento privado de otro módulo. Los números de contrato remiten a una sola definición en el documento compartido.

## 9. Decisiones y preguntas abiertas

### Decisiones tomadas

- **S05-D-01** — RF-02..RF-05/RF-15/RF-19 definen comportamiento; interrupción local más cancelación de servidor es diseño propuesto del 2026-10-29.

### Preguntas abiertas

- **S05-P-01 — bloqueante G0:** Validar captura/conversión y perfil/cabecera de audio en spike; B con A/C antes de implementar streaming.
- **S05-P-02 — bloqueante G1:** Elegir ASR/LLM/TTS/VAD y parte no escuchada; B con C, ADR-004 antes de demo real.
- **S05-P-03 — bloqueante G3:** Medir reacción y acordar umbral con SPEC-01; B/C antes de aceptar interrupciones.

Una pregunta bloqueante detiene únicamente la interfaz o integración indicada. Se puede avanzar con fixtures del contrato congelado y en trabajo independiente; no conectar una interfaz incompatible por suposición.

## 10. Verificación

**Estado:** plan de pruebas e inspecciones; ninguna prueba de producto se ha ejecutado al redactar esta spec. Adjuntar resultados y versiones al cerrar cada criterio.

| RF/RNF/RT | Prueba o inspección | Evidencia esperada |
| --- | --- | --- |
| S05-RF-01 → S05-CA-01 | UI/navegador; denegado, ausente y concedido. | Escenario CA-01 satisfecho y evidencia adjunta al cierre. |
| S05-RF-02 → S05-CA-02 | Integración/canal; captura y rechazo por estado. | Escenario CA-02 satisfecho y evidencia adjunta al cierre. |
| S05-RF-03 → S05-CA-03 | Integración/corpus; ASR→tutor→TTS real y respuestas revisadas. | Escenario CA-03 satisfecho y evidencia adjunta al cierre. |
| S05-RF-04 → S05-CA-04 | Contrato/UI; stream de mensajes repetidos y desordenados. | Escenario CA-04 satisfecho y evidencia adjunta al cierre. |
| S05-RF-05 → S05-CA-05 | Integración/audio; traza de interrupción y generaciones. | Escenario CA-05 satisfecho y evidencia adjunta al cierre. |
| S05-RF-06 → S05-CA-06 | Rendimiento/integración; tarea lenta y traza de cola. | Escenario CA-06 satisfecho y evidencia adjunta al cierre. |
| S05-RF-07 → S05-CA-07 | Inyección de fallos; UI y estado correlacionados. | Escenario CA-07 satisfecho y evidencia adjunta al cierre. |
| RF-02, RF-03, RT-01 | Audio real ASR→LLM→TTS en escritorio | Grabación de demo autorizada o traza técnica sin guardar conversación completa. |
| RF-04, RF-05 | UI y corpus de tutor con errores deliberados | Transcripción sin marcas y correcciones reservadas. |
| RF-15, RNF-01 | Interrupción con frames tardíos y medición | Tiempos y resultado audible. |
| RF-19 | Permisos y ausencia de dispositivo | Ningún envío previo a consentimiento. |
| RNF-02 | Evaluador lento y carga de GPU | Turnos siguen; cola acotada. |
| RNF-08 | Corpus de temas y solicitudes fuera del contexto | Respuestas conforme a política aprobada. |
| RNF-12, RNF-13 | Controles/idiomas, origen cifrado y secretos | Inspección web y configuración. |

## 11. Esfuerzo, riesgos y consecuencias

- **Esfuerzo:** L: audio en navegador, tres adaptadores, interrupciones y UI. Separar hitos de fixture, un turno real y conversación continua.
- **Riesgos:** Eco, falsas detecciones, memoria GPU compartida y salida tardía; el spike de G0 evita diseñar sobre un formato no soportado.
- **Consecuencias:** Sin evaluación en vivo ni reanudación; las limitaciones de navegador/red deben declararse en SPEC-12.
