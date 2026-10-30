# Trazabilidad del catálogo a las specs

**Estado:** plan, 2026-10-29; actualizado el 2026-10-30. Fuente: [REQUIREMENTS.md](../REQUIREMENTS.md). [Volver al plan](README.md).

La spec primaria responde por el cumplimiento de cada requisito; las colaboradoras implementan contratos o verifican el recorrido integrado. Los IDs locales refinan el catálogo y no lo reemplazan. Las referencias `SNN-RF-MM / CA-MM` remiten al criterio `SNN-CA-MM` dentro de SPEC-NN; las filas de §10 cubren también restricciones transversales. Todas las verificaciones de producto están pendientes.

| Catálogo | Spec primaria | Specs colaboradoras | Requisitos/criterios o verificación |
| --- | --- | --- | --- |
| RF-01 | [SPEC-02](SPEC-02-content-and-catalog.md) | 04, 05, 12 | S02-RF-01 / CA-01; S02-RF-04 / CA-04; S04-RF-01 / CA-01; S12-RF-02 / CA-02 |
| RF-02 | [SPEC-05](SPEC-05-voice-conversation.md) | 06, 12 | S05-RF-02 / CA-02 |
| RF-03 | [SPEC-05](SPEC-05-voice-conversation.md) | 04, 12 | S05-RF-03 / CA-03; S05-RF-07 / CA-07 |
| RF-04 | [SPEC-05](SPEC-05-voice-conversation.md) | 09, 12 | S05-RF-04 / CA-04 |
| RF-05 | [SPEC-05](SPEC-05-voice-conversation.md) | 02, 09, 12 | S05-RF-03 / CA-03 |
| RF-06 | [SPEC-08](SPEC-08-phonetic-evaluation.md) | 01, 09, 12 | S08-RF-01 / CA-01 |
| RF-07 | [SPEC-07](SPEC-07-anchor-phrases.md) | 02, 08, 12 | S02-RF-02 / CA-02; S07-RF-01 / CA-01; S07-RF-02 / CA-02; S07-RF-06 / CA-06 |
| RF-08 | [SPEC-09](SPEC-09-final-report.md) | 04, 07, 12 | S04-RF-06 / CA-06; S09-RF-01 / CA-01; S09-RF-02 / CA-02; S09-RF-03 / CA-03; S09-RF-04 / CA-04; S09-RF-05 / CA-05; S09-RF-06 / CA-06; S09-RF-07 / CA-07 |
| RF-09 | [SPEC-06](SPEC-06-audio-and-consent.md) | 02, 09, 10, 12 | S02-RF-02 / CA-02; S06-RF-03 / CA-03; S06-RF-04 / CA-04; S10-RF-02 / CA-02 |
| RF-10 | [SPEC-06](SPEC-06-audio-and-consent.md) | 03, 04, 05, 12 | S06-RF-01 / CA-01; S06-RF-02 / CA-02 |
| RF-11 | [SPEC-03](SPEC-03-identity-and-access.md) | 04, 12 | S03-RF-01 / CA-01; S03-RF-02 / CA-02; S03-RF-03 / CA-03; S03-RF-04 / CA-04 |
| RF-12 | [SPEC-10](SPEC-10-history-and-comparison.md) | 08, 09, 12 | S10-RF-01 / CA-01; S10-RF-02 / CA-02; S10-RF-04 / CA-04 |
| RF-13 | [SPEC-04](SPEC-04-session-orchestration.md) | 05, 07, 12 | S04-RF-03 / CA-03; S04-RF-04 / CA-04 |
| RF-14 | [SPEC-06](SPEC-06-audio-and-consent.md) | 08, 09, 12 | S06-RF-03 / CA-03; S09-RF-02 / CA-02; S09-RF-05 / CA-05 |
| RF-15 | [SPEC-05](SPEC-05-voice-conversation.md) | 04, 12 | S05-RF-05 / CA-05; S12-RF-02 / CA-02 |
| RF-16 | [SPEC-11](SPEC-11-data-deletion.md) | 03, 06, 10, 12 | S11-RF-01 / CA-01; S11-RF-02 / CA-02; S11-RF-03 / CA-03; S11-RF-06 / CA-06; S12-RF-04 / CA-04 |
| RF-17 | [SPEC-07](SPEC-07-anchor-phrases.md) | 04, 08, 12 | S07-RF-03 / CA-03; S07-RF-04 / CA-04; S07-RF-05 / CA-05; S07-RF-06 / CA-06; S07-RF-07 / CA-07; S12-RF-03 / CA-03 |
| RF-18 | [SPEC-04](SPEC-04-session-orchestration.md) | 05, 06, 07, 08, 09, 12 | S04-RF-04 / CA-04; S04-RF-05 / CA-05; S04-RF-06 / CA-06; S04-RF-07 / CA-07; S05-RF-07 / CA-07; S07-RF-07 / CA-07; S08-RF-06 / CA-06; S09-RF-06 / CA-06; S12-RF-03 / CA-03; S12-RF-06 / CA-06 |
| RF-19 | [SPEC-05](SPEC-05-voice-conversation.md) | 04, 12 | S05-RF-01 / CA-01; S12-RF-03 / CA-03 |
| RF-20 | [SPEC-06](SPEC-06-audio-and-consent.md) | 10, 11, 12 | S06-RF-05 / CA-05; S10-RF-03 / CA-03; S11-RF-01 / CA-01; S12-RF-04 / CA-04 |
| RNF-01 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 04, 05, 12 | S01-RF-05 / CA-05; S12-RF-05 / CA-05; SPEC-01 §10 y SPEC-12 §10 |
| RNF-02 | [SPEC-05](SPEC-05-voice-conversation.md) | 00, 08, 12 | S00-RF-02 / CA-02; S05-RF-06 / CA-06; S08-RF-05 / CA-05; SPEC-05 §10 y SPEC-12 §10 |
| RNF-03 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 08, 12 | S01-RF-02 / CA-02; S01-RF-04 / CA-04; S12-RF-05 / CA-05; SPEC-01 §10 y SPEC-12 §10 |
| RNF-04 | [SPEC-09](SPEC-09-final-report.md) | 08, 12 | S08-RF-01 / CA-01; S08-RF-06 / CA-06; S09-RF-02 / CA-02; S09-RF-03 / CA-03; SPEC-09 §10 y SPEC-12 §10 |
| RNF-05 | [SPEC-08](SPEC-08-phonetic-evaluation.md) | 01, 09, 12 | S01-RF-06 / CA-06; S08-RF-02 / CA-02; S09-RF-02 / CA-02; S09-RF-04 / CA-04; SPEC-08 §10 y SPEC-12 §10 |
| RNF-06 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 02, 08, 09, 12 | S01-RF-06 / CA-06; S02-RF-05 / CA-05; S08-RF-07 / CA-07; S09-RF-07 / CA-07; SPEC-01 §10 y SPEC-12 §10 |
| RNF-07 | [SPEC-06](SPEC-06-audio-and-consent.md) | 11, 12 | S06-RF-02 / CA-02; S06-RF-05 / CA-05; S06-RF-06 / CA-06; S06-RF-07 / CA-07; S11-RF-02 / CA-02; S11-RF-04 / CA-04; S11-RF-06 / CA-06; S12-RF-04 / CA-04; S12-RF-06 / CA-06; SPEC-06 §10 y SPEC-12 §10 |
| RNF-08 | [SPEC-05](SPEC-05-voice-conversation.md) | 02, 12 | S02-RF-04 / CA-04; SPEC-05 §10 y SPEC-12 §10 |
| RNF-09 | [SPEC-03](SPEC-03-identity-and-access.md) | 04, 06, 07, 10, 11, 12 | S03-RF-01 / CA-01; S03-RF-04 / CA-04; S03-RF-05 / CA-05; S06-RF-04 / CA-04; S10-RF-05 / CA-05; S11-RF-03 / CA-03; S11-RF-05 / CA-05; S12-RF-04 / CA-04; S12-RF-07 / CA-07; SPEC-03 §10 y SPEC-12 §10 |
| RNF-10 | [SPEC-04](SPEC-04-session-orchestration.md) | 12 | S04-RF-01 / CA-01; S04-RF-02 / CA-02; S04-RF-07 / CA-07; S12-RF-06 / CA-06; SPEC-04 §10 y SPEC-12 §10 |
| RNF-11 | [SPEC-10](SPEC-10-history-and-comparison.md) | 02, 08, 12 | S02-RF-03 / CA-03; S08-RF-04 / CA-04; S10-RF-04 / CA-04; S10-RF-05 / CA-05; SPEC-10 §10 y SPEC-12 §10 |
| RNF-12 | [SPEC-12](SPEC-12-acceptance-and-demo.md) | 00, 02, 03, 04, 05, 06, 07, 09, 10, 11 | S00-RF-05 / CA-05; SPEC-12 §10 |
| RNF-13 | [SPEC-12](SPEC-12-acceptance-and-demo.md) | 00, 03, 05, 06 | S00-RF-02 / CA-02; S00-RF-04 / CA-04; S00-RF-05 / CA-05; S03-RF-06 / CA-06; S12-RF-01 / CA-01; SPEC-12 §10 |
| RNF-14 | [SPEC-08](SPEC-08-phonetic-evaluation.md) | 01, 07, 12 | S01-RF-06 / CA-06; S07-RF-02 / CA-02; S07-RF-03 / CA-03; S08-RF-03 / CA-03; SPEC-08 §10 y SPEC-12 §10 |
| RT-01 | [SPEC-05](SPEC-05-voice-conversation.md) | 12 | S05-RF-03 / CA-03; S12-RF-01 / CA-01; SPEC-05 §10 y SPEC-12 §10 |
| RT-02 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 08, 12 | S01-RF-03 / CA-03; S12-RF-05 / CA-05; SPEC-01 §10 y SPEC-12 §10 |
| RT-03 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 12 | S01-RF-01 / CA-01; S01-RF-04 / CA-04; SPEC-01 §10 y SPEC-12 §10 |
| RT-04 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 12 | S01-RF-03 / CA-03; SPEC-01 §10 y SPEC-12 §10 |
| RT-05 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 09, 12 | S01-RF-07 / CA-07; SPEC-01 §10 y SPEC-12 §10 |
| RT-06 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 09, 12 | S01-RF-07 / CA-07; SPEC-01 §10 y SPEC-12 §10 |
| RT-07 | [SPEC-01](SPEC-01-experiments-and-evaluator-selection.md) | 12 | S01-RF-01 / CA-01; S12-RF-05 / CA-05; SPEC-01 §10 y SPEC-12 §10 |

## Decisiones del catálogo

| Decisión | Implementación y punto de control |
| --- | --- |
| D-01 Historial sin nota/mapa | SPEC-09/10; G2 (usuario base) y G3 (por cuenta) |
| D-02 Niveles/temas/tiempo | SPEC-02/04/05; G1 y G2 |
| D-03 Frases/referencia/idiomas | SPEC-02/07/09; G1 y G2 |
| D-04 Consentimiento, 30 días y borrado | SPEC-06/11; G1 y G3 |
| D-05 Orientación de modelos, GPU y presupuesto | SPEC-00/01/12; G0, G1 y G3 |
| D-06 Escritorio, cupo e interrupción | SPEC-04/05/12; G2 y G3 |
| D-07 Validez/reintentos/incertidumbre/recuperación | SPEC-04/07/08/09; G2 (anclas y fallo de modelo) y G3 (incertidumbre de conversación y corte de canal) |
| D-08 Latencia por medir | SPEC-01/12; G3 |
| D-09 Cuentas sin recuperación por correo | SPEC-03; G3 (iteración 2) |
| D-10 Datos públicos y métricas | SPEC-01/12; protocolo E0 y resultados G3 |
| D-11 Selección tras comparación | SPEC-01/08; preliminar G1 y decisión final G3 |
| D-12 Calendario y pitch | Plan por iteraciones y SPEC-12; G2 y G3 |
| D-13 Ejecución local, acceso al auditorio y nube | SPEC-00/12; G0, G2 (acceso) y final de la iteración 2 (nube) |
| D-14 Recorte en dos iteraciones y V3 | Plan por iteraciones; todos los gates |
| D-15 Criterios del pitch | SPEC-12; G3 |
| D-16 Corpus interno del equipo | SPEC-06/01; G1 (copia) y G3 (RT-06 y WER) |
| D-17 Desviación de RF-18 en la iteración 1 | SPEC-04/05/07; G2 (desviación) y G3 (corrección) |
| D-18 Consentimiento y usuario base | SPEC-03/06; G1 (usuario base y consentimiento sembrado) y G3 (texto de consentimiento) |

## Criterios de aceptación de la demostración

El alcance de cada criterio en la iteración 1 y en el pitch está en el [plan por iteraciones](../ROADMAP.md) (D-15). SPEC-12 reparte la verificación: B ejecuta los recorridos y C aporta las métricas.

| Criterio de REQUIREMENTS.md §8 | Specs que lo construyen | Verificación final | Responsable de verificación |
| --- | --- | --- | --- |
| 1 Cuenta y práctica con voz sin corrección en vivo | 02, 03, 04, 05, 06 | S12-CA-02 | B |
| 2 Interrumpir al tutor | 04, 05 | S12-CA-02 y métricas S12-CA-05 | B; C las métricas |
| 3 Cinco anclas e informe válido | 02, 04, 06, 07, 08, 09 | S12-CA-02 | B |
| 4 Muestra recuperada e intentos agotados | 04, 06, 07, 08 | S12-CA-03 | B |
| 5 Historial, audio y comparación | 06, 08, 09, 10 | S12-CA-02 | B |
| 6 Borrado, caducidad y aislamiento | 03, 06, 11 | S03-CA-05 y S12-CA-07 (aislamiento, obligatorio en el pitch); S12-CA-04 (borrado y caducidad, si alcanza) | B |
| 7 Micrófono, cupo, fallos y recarga | 04, 05, 06, 07 | S12-CA-03 y S12-CA-06 | B |
| 8 Mediciones y calidad pública | 01, 08, 09, 12 | S12-CA-05 | C |

## Fuera de alcance conservado

Francés/alemán, mapa de vocales, nota global, verificación/recuperación por correo, múltiples conversaciones simultáneas, reanudación tras recarga, grabaciones propias obligatorias, comparación con monólogos y piloto longitudinal no tienen spec de implementación en este MVP. No asignarles trabajo como si fueran requisitos pendientes del producto actual.
