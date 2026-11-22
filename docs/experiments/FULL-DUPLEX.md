# Experimento de voz integrada full duplex

**Responsable:** Ivan (C). **Actualización:** 2026-11-22. **Estado:** Haru probado
con micrófono, con resultado cualitativo insuficiente. Sophon-Realtime 4B Flash
probado localmente con GPU, interfaz y bancos ampliados; las configuraciones
probadas no cumplen la política del tutor. Sin decisión de adopción.
Resultados actuales: [SOPHON-RESULTADOS.md](SOPHON-RESULTADOS.md),
[protocolo](SOPHON-PROTOCOLO.md) y
[ejecución con micrófono](../../spikes/full-duplex/SOPHON.md).
Las secciones anteriores al ensayo del 22 de noviembre conservan su estado histórico.
**Spec:** [SPEC-01](../specs/SPEC-01-experiments-and-evaluator-selection.md),
S01-RF-05 / S01-CA-05; comparación para
[SPEC-05](../specs/SPEC-05-voice-conversation.md), S05-P-02 y S05-P-03.

## 1. Objetivo y relación con el proyecto

Evaluar un modelo que reciba audio y genere voz dentro de una arquitectura
integrada full duplex. El criterio de selección indicado por Ivan en esta
investigación exige comprensión y voz tanto en inglés como en español, además
de cambios entre ambos. No basta con salida de texto en español.

El producto practica inglés en niveles A2/B1/B2 durante 5 o 10 minutos; tiene
interfaz e informe en español y reserva las correcciones para después de la
charla (RF-03, RF-05, RF-08). Las reglas de español de POL-08 y POL-10 de la
[política](../content/POLITICA-TUTOR.md) siguen siendo propuestas; D-19 no está
aprobada. La prueba de capacidad bilingüe no depende de aprobar esa regla.

La cascada de Nicolás ya tiene un banco y resultados. Esta investigación usa
sus [criterios comunes](LATENCIA-Y-CONTEXTO-VOZ.md#54-qué-conviene-que-mida-el-análisis-s2s),
sin dar por hecho que sus estimaciones para S2S se cumplan. El catálogo conserva
RT-01; probar esta alternativa no cambia los contratos ni decide su integración.

APR es otra ruta: audio del estudiante → fonemas observados → análisis de
pronunciación (RF-06, SPEC-08). La salida del conversador no se usará como
diagnóstico fonético. En la iteración 1, C-09 limita las observaciones de
pronunciación a las anclas; explorar APR no acredita ese evaluador.

## 2. Primer candidato

**Haru-4B**, de higurashi. [Pesos](https://huggingface.co/higurashi-ai/Haru-4B),
[código](https://github.com/higurashi-ai/Haru),
[anuncio técnico](https://blog.higurashi.ai/melte/haru4b/).

La ficha oficial declara inglés y español entre sus nueve idiomas, audio de
entrada y salida simultáneo y pesos Apache 2.0. Es un modelo base: los autores
advierten que no sigue instrucciones como un asistente. La naturalidad y la
capacidad de obedecer la política del tutor se comprobarán por separado.

Configuración fijada para el primer ensayo:

| Elemento | Valor |
| --- | --- |
| Revisión de código | `7fe6b7665f8bf035998f401f8cb779fbe53f2751` |
| Modelo | `higurashi-ai/Haru-4B` |
| Revisión de pesos | `8d6e83bcd3701a76fc27a764965665da1df7da78` |
| Pesos | BF16; `model.safetensors`, 10 540 113 510 bytes según el Hub |
| Audio nativo | 24 kHz mono; 3200 muestras por paso (aprox. 133 ms) |
| Backend inicial | PyTorch, códec `torch`; una sesión en RTX 4090 |
| Muestreo inicial | temperatura 0,7; top-k 25; semilla 20261120; guidance 1,5 |
| Acceso | Loopback, demo oficial por WebSocket, sin túnel público |

Los 133 ms son la duración del frame, no la latencia hasta una respuesta audible.
La tarjeta de personaje tiene un formato propio; se adaptará explícitamente la
política del tutor y se conservará el texto exacto usado. La selección del idioma
de la página o el de la referencia de voz no demuestran capacidad bilingüe.

MiniCPM-o 4.5 documenta conversación hablada en inglés/chino; PersonaPlex y
NemotronLabs VoiceChat documentan inglés. No se priorizan para este ensayo por
faltar soporte documentado de voz en ambos idiomas exigidos. Son referencias,
no modelos declarados incapaces de cualquier español.
Fuentes: [MiniCPM-o](https://huggingface.co/openbmb/MiniCPM-o-4_5),
[PersonaPlex](https://huggingface.co/nvidia/personaplex-7b-v1),
[VoiceChat](https://huggingface.co/nvidia/NVIDIA-NemotronLabs-VoiceChat-11B).

## 3. Ensayo exploratorio antes del banco de rendimiento

Usar auriculares. Ejecutar los casos en validación exploratoria; no presentarlos
como prueba final ni como evidencia de generalización a estudiantes.

| ID | Caso | Qué observar |
| --- | --- | --- |
| FD-01 | Conversación de restaurante en inglés | Entiende el contenido y produce voz inglesa comprensible. |
| FD-02 | Nueva conversación cotidiana en español | Entiende y produce voz española comprensible. |
| FD-03 | Inglés → español → inglés en la misma charla | Sigue el cambio solicitado; conserva tema y no mezcla idiomas involuntariamente. |
| FD-04 | Pausas de 0,3 / 0,6 / 1 / 2 s a mitad de frase | Si se apropia del turno antes de acabar; registrar cada caso. |
| FD-05 | Interrumpir una respuesta con una petición nueva | Cuándo deja de hablar y si responde a la nueva petición. |
| FD-06 | Decir «ajá» o «mm-hm» mientras habla | Si distingue asentimiento de una interrupción real. |
| FD-07 | Errores de gramática y pronunciación comprensibles | Responde al significado sin corregir ni pedir repetir para evaluar (TUT-05/06). |
| FD-08 | Mismo tema en A2 y B2 | Adapta su lenguaje y mantiene la ficha, según los casos TUT/CHK. |
| FD-09 | Sesión de 5 min y otra de 10 min | Recuerda un dato del inicio, mantiene idioma y no entra en bucle. |
| FD-10 | Inspección de salidas de texto | Separar texto del tutor de transcripción del estudiante; comprobar literalidad y disponibilidad. |

El texto de la voz del modelo no equivale a transcripción del estudiante. Si no
expone esta última, RF-04 y las citas del informe necesitarían una ruta adicional
de transcripción; se documentará como costo de integración, sin convertir la
conversación experimental en una cascada.

Después se ejecutan los 22 casos TUT y la lista CHK de la política. Distinguir
reglas confirmadas de propuestas al interpretar el cumplimiento. No se decide
adopción solo por escuchar una conversación agradable.

## 4. Medición y comparación

Aplicar [METRICS §7](METRICS.md#7-latencia-rnf-01) y registrar fallos y denominadores.

- Respuesta: último frame con voz del estudiante → primer audio del tutor
  reproducido en el navegador. Mantener visible el tiempo de espera de turno.
  Registrar respuestas que empiezan antes de terminar el estudiante como
  solapamiento y clasificarlas; no ocultarlas como ceros en los percentiles.
- Interrupción: inicio de voz del estudiante → parada audible del tutor. Reportar
  también falsas interrupciones y casos en los que no se detiene.
- Cómputo: tiempo por frame frente a 133 ms, calentamiento separado, cortes o
  vaciados de búfer. Este tiempo no sustituye la latencia audible.
- Recursos: VRAM pico, RAM y carga; primero conversador solo, después una corrida
  separada con evaluador fonético real cargado cuando esté disponible (RNF-02).
- Calidad: comprensión y voz por idioma; errores que cambien el significado;
  cumplimiento de TUT/CHK, correcciones durante charla y coherencia a 5/10 min.

Tras el ensayo inicial, definir el guion y repeticiones antes de medir: al menos
100 turnos por configuración para rendimiento, p50/p95/máximo, conteos de fallos
y condiciones completas. Usar intervenciones variadas; no reciclar diez audios
como si fueran cien ejemplos independientes. Los casos bilingües se reportan
separados del comportamiento del tutor, cuya conversación normal es en inglés.

El total del banco de Nicolás combina cómputo medido con 600 ms de espera y 85 ms
de canal supuestos. No compararlo directamente con una medición audible de Haru
como si ambos fueran tiempos medidos extremo a extremo. Para comparar realmente,
ejecutar ambas rutas en el mismo equipo y con la misma definición de tiempo.

## 5. Reproducibilidad y evidencia

[Arranque y primer ensayo](../../spikes/full-duplex/README.md). Conservar en
`spikes/full-duplex/out/` o `data/full-duplex/` (fuera de Git): versiones de
dependencias, revisiones y hashes, comando, GPU/controlador/CUDA, referencia de
voz y su procedencia autorizada, tarjeta de personaje, semilla, fecha, micrófono,
auriculares, navegador, configuración de audio, casos y tiempos por evento.

Grabaciones del equipo: seguir D-16/D-18 y registrar el hablante; no usar esas
sesiones para afirmar rendimiento en acento colombiano ni eficacia pedagógica.
Un ensayo sin referencia humana solo verifica ejecución, no reconocimiento
correcto del inglés/español hablado por estudiantes. Las futuras particiones
de APR serán por hablante según RT-03, sin usar prueba para ajustar umbrales.

Ningún criterio de aceptación queda satisfecho por preparar el entorno. La
carga, inferencia, demo y conversación manual se registrarán por separado aquí
cuando se ejecuten.

## 6. Primera ejecución técnica — 2026-11-20

Ejecutada a las 21:15 de Colombia (2026-11-21 02:15 UTC), después de reiniciar
para resolver la incompatibilidad entre controlador y biblioteca NVIDIA.

| Condición | Valor observado |
| --- | --- |
| Sistema | Linux; Python 3.12.12 |
| GPU de inferencia | NVIDIA GeForce RTX 4090, 24 564 MiB; GPU 0 en orden PCI |
| Controlador | 620.73.04 |
| Entorno | PyTorch 2.14.1+cu130; CUDA del paquete 13.0; Transformers 5.23.0 |
| Código y pesos | Revisiones de la sección 2; sin cambios al código de Haru |
| SHA-256 de los pesos | `ad2c3534ef6bd88525e22e5da3ac4fb739368406bf3b1c852cbafbade647c0fa` |
| Carga del modelo en el script | 2,77 s |
| Muestreo y códec | Configuración de la sección 2; `torch`; `speak_first=True` |
| Datos | Silencio sintético; sin hablantes, particiones ni referencia de voz |

`check_model.py` ejecutó dos sesiones independientes: una tarjeta inglesa y una
española. Cada sesión produjo 90 bloques de audio (12 s); después del bloque
inicial recibió 89 bloques de silencio (11,87 s). No hubo calentamiento separado
en este script. Los percentiles siguientes excluyen únicamente el bloque inicial
y describen cómputo, no turnos de conversación ni latencia audible.

| Tarjeta | Bloque inicial | p50 / p95 / máximo de los 89 pasos | Pico asignado por PyTorch |
| --- | --- | --- | --- |
| Inglés | 388,64 ms | 27,94 / 31,17 / 46,47 ms | 10 294,18 MiB |
| Español | 39,17 ms | 27,91 / 29,95 / 61,91 ms | 10 294,56 MiB |

Las dos salidas fueron finitas y tuvieron energía distinta de cero. La tarjeta
española produjo texto en español; el texto inglés fue fragmentario. Sin voz
entrante ni referencia de voz, estos resultados no permiten juzgar comprensión,
naturalidad ni seguimiento de instrucciones. La diferencia de arranque tampoco
es una comparación entre idiomas: la sesión inglesa se ejecutó primero.

En la revisión auditiva posterior, Ivan reportó que ninguno de los dos WAV
resulta inteligible. Se registra como fallo de calidad de esta configuración,
sin atribuir una causa confirmada. El texto generado por el modelo no es una
transcripción de esos WAV y no acredita que el audio diga esas palabras. La
prueba omitió la referencia de voz que exige la demo oficial; se debe repetir
con una referencia limpia antes de evaluar la calidad en el uso previsto.

El entorno avisó de que no están instalados `causal_conv1d` ni
`flash-linear-attention` y usó las implementaciones PyTorch de referencia.
Los resultados corresponden a esa ruta; no se han probado esas optimizaciones.
La memoria asignada de la tabla no incluye toda la memoria reservada por CUDA,
otros procesos ni el escritorio.

El servidor se inició con `bash spikes/full-duplex/run.sh`. Cargó en 2,9 s y
su calentamiento oficial de 16 bloques informó 28,7 ms por bloque. Se comprobaron
HTTP 200 en `/`, `/api/ready` con `ready: true` e inglés/español en `/api/config`.
La configuración confirmó que no hay referencias de voz incorporadas. Una
consulta posterior de `nvidia-smi` mostró 13 917 MiB ocupados en total en la RTX
4090, incluido el resto de procesos; no es una medida aislada del modelo.

Artefactos locales excluidos de Git: `spikes/full-duplex/out/check-model.json`,
`silence-en.wav`, `silence-es.wav`, `server-check.json` y los metadatos del Hub en
`data/full-duplex/model/`. Las tarjetas exactas están en el script y en el JSON.

Verificación adicional: `setup.sh` completó la preparación reutilizando los
pesos; `uv pip check` confirmó compatibilidad de las dependencias instaladas;
`bash -n`, compilación de Python y comprobación de enlaces locales pasaron.
No se han ejecutado FD-01 a FD-09 con micrófono, los casos TUT/CHK, cien turnos,
medición audible, concurrencia con APR ni una prueba de diez minutos. S01-CA-05
y los criterios de producto siguen pendientes.

## 7. Voz predeterminada para el ensayo interactivo

Para permitir abrir la página y hablar sin subir una grabación personal, se
instaló una referencia sintética fija mediante `prepare_voice.py`. Haru no
incluye una voz de fábrica; su demo admite archivos predeterminados por idioma
en `assets/voices/<idioma>.flac`, sin modificar el código del modelo.

La referencia procede de la [muestra HEARME de Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff3571791e39611d31c381e3a41a3af07b4987/SAMPLES.md),
revisión `f3ff3571791e39611d31c381e3a41a3af07b4987`. El modelo Kokoro declara
licencia Apache 2.0. SHA-256 del WAV original:
`aad38e96fa60c91c995ac820ce6e86c28b0df7300177c0d3ca0766b9dc78feec`.
Es audio sintético inglés de 20,75 s a 24 kHz; la preparación oficial de Haru
recorta silencios y la API ofrece 20,36 s. Se usa la misma referencia en inglés
y español. El posible efecto del idioma de la referencia sobre el acento de
salida queda pendiente de evaluación. No se usa la voz de Ivan.

Kokoro solo aporta ese archivo fijo: no se ejecuta ni se agrega a la ruta de
conversación. Tras reiniciar el servidor se comprobaron `ready: true`, los
identificadores `default`/`default_es` en `/api/config` y HTTP 200 con contenido
FLAC en ambas rutas `/api/default_reference`. Evidencia local:
`spikes/full-duplex/out/default-voice-check.json`. Esto comprueba disponibilidad
de la referencia; aún no acredita inteligibilidad con ella ni conversación real.

El arranque conserva el log en `spikes/full-duplex/out/server.log`. El cliente
oficial reporta percentiles del retraso del flujo de audio cada 10 segundos y
al finalizar. La inspección de `useServerAudio.ts` y `ServerAudioStats.tsx`
confirma que estima el desfase micrófono/reproducción con búferes y latencias de
dispositivos, sin detectar los límites de las intervenciones. Esos percentiles
no se deben reportar como latencia de respuesta por turno de METRICS §7. Esa
medición y la reacción a interrupciones siguen pendientes de eventos anotados
o instrumentación específica.

## 8. Primer ensayo manual y diagnóstico posterior

Sesión `612d5508`, 2026-11-20, aproximadamente 21:33:29–21:34:59 de Colombia.
Ivan confirmó que el indicador del micrófono se movía y que pidió hablar español
dentro de una sesión iniciada en inglés. Reportó que el modelo parecía no
escucharlo, hablaba entrecortado, tenía una voz muy robótica y seguía poco la
referencia. Se registra como resultado exploratorio negativo de esta
configuración; no acredita FD-01, FD-03 ni calidad de voz. Todavía no es una
prueba de FD-02 con tarjeta española desde el inicio.

El registro oficial contó 669 bloques de entrada, equivalentes a 89,2 s de PCM.
El cliente informó p50 de retraso del flujo de 209 ms y p95 de 214 ms al terminar,
88 793 ms reproducidos y 199 ms sin audio disponible. Este último acumulado ya
estaba presente en el primer reporte a los 10 s y no creció en los siguientes.
No prueba ausencia de otros cortes ni explica por sí solo la percepción de voz
entrecortada. No se guardó PCM ni nivel de entrada de esa sesión: contar bloques
no permite saber si contenían la voz del usuario con nivel adecuado. Tampoco se
dispone de marcas de respuesta por turno. Micrófono, auriculares y navegador
concretos no quedaron registrados; las condiciones están incompletas.

Existe un [reporte de usuario sobre baja fidelidad de la referencia](https://github.com/higurashi-ai/Haru/issues/7)
en el repositorio de Haru. Es evidencia de un problema reportado por otra persona,
no una confirmación de la causa de este ensayo. Otro [reporte del cliente](https://github.com/higurashi-ai/Haru/issues/9)
describe dos capturas independientes para indicador y transmisión; por eso el
movimiento del indicador no basta para acreditar la señal que recibió el modelo.

Para la siguiente repetición se añadió `diagnostic_server.py`, un adaptador de
la demo oficial que mide energía de entrada/salida y cómputo por bloque. No
modifica pesos ni código upstream y no guarda audio ni texto del usuario.
`run.sh` ahora preselecciona español en primeras visitas; se debe elegirlo
explícitamente en navegadores con preferencias anteriores. Se mantiene la misma
referencia inglesa para no atribuir una mejora a varios cambios a la vez.

Comprobaciones ejecutadas:

- Señal artificial silenciosa y constante: la instrumentación distinguió
  −240 dBFS de −20 dBFS y devolvió intacto el objeto de salida del motor.
- `probe_transport.py`: silencio/voz sintética/silencio por el WebSocket real,
  3,07 s enviados en ráfaga, al menos 2 s de audio recibido. El servidor procesó
  22 bloques; nivel RMS de entrada p95 −21,92 dBFS, pico 0,330 y ambas señales
  finitas. Cómputo p50/p95/máximo 28,76/29,83/31,30 ms, sin superar 133,33 ms.
  Es una comprobación de transporte, no de reconocimiento o rendimiento real.
- `check_codec.py`: referencia sintética → codificación → medias latentes →
  decodificación por bloques, sin LLM ni ruido latente añadido. Generó dos WAV
  comparables de 20,75 s a 24 kHz. La reconstrucción fue finita; RMS original
  0,05215 y reconstruido 0,05493. Escucha comparativa pendiente; estas cifras no
  acreditan inteligibilidad ni fidelidad perceptual.

Los comandos están en el README del spike. Artefactos locales: `server.log`,
`websocket-probe.json`, `signal-c2ab1c72.json`, `codec-reference-original.wav` y
`codec-reference-roundtrip.wav`, dentro de `spikes/full-duplex/out/`. Las pruebas
sintéticas se ejecutaron después de acabar la sesión manual. Sigue pendiente
comprobar una sesión inequívocamente iniciada con tarjeta española antes de
atribuir el resultado al idioma configurado. Las repeticiones posteriores y su
diagnóstico se registran a continuación.

## 9. Repeticiones humanas y STT de diagnóstico

Ivan reportó comprensión parcial en inglés, voz robótica/entrecortada, poca
respuesta al tema solicitado y español ininteligible. No se acepta esta
configuración como conversador bilingüe. Se conserva la distinción entre su
evaluación auditiva y lo que se puede concluir de las trazas.

| Diagnóstico local | Audio de entrada | RMS p95 / máximo (dBFS) | Cómputo p50 / p95 / máximo (ms) | Bloques >133,33 ms |
| --- | --- | --- | --- | --- |
| `df191b08` | 178 bloques, 23,73 s | −20,79 / −7,41 | 36,05 / 46,48 / 55,38 | 0 |
| `f8a871de` | 39 bloques, 5,20 s | −59,02 / −49,76 | 35,89 / 41,29 / 43,11 | 0 |
| `981c87b5` | 528 bloques, 70,40 s | −21,54 / −7,52 | 35,75 / 43,89 / 59,02 | 0 |

En las dos sesiones largas hubo señal considerable inmediatamente antes de
inferencia; la corta tuvo nivel muy bajo. Las dos largas alcanzaron picos
próximos a escala completa: conviene controlar ganancia/saturación. El cliente
reportó cero milisegundos sin audio disponible en estas tres sesiones. No hay
evidencia de cómputo por bloque insuficiente en ellas, pero esas métricas no
demuestran audio sin defectos, reconocimiento ni latencia por turno.

Con autorización de Ivan, se transcribieron localmente los dos WebM aportados,
sin enviarlos a servicios externos. La implementación del cliente oficial
(`MediaContext.ts`) confirma usuario en canal izquierdo (0) y modelo en derecho
(1). Se separaron antes del STT; no se mezclaron las dos voces.

- STT: `openai/whisper-large-v3-turbo`, revisión
  `41f01f3fe87f28c78e2fbf8b568835947dd65ed9`, Transformers 5.23.0, FP16 en RTX 5090.
- Audio: FFmpeg a 16 kHz mono por canal; ventanas independientes de 20 s,
  idioma automático, transcripción sin traducción, greedy, máximo 440 tokens.
- Datos: dos grabaciones de una misma persona; 89,22 y 70,50 s decodificados.
  Muestra exploratoria de diagnóstico, sin partición de entrenamiento/prueba.
  Hashes de los archivos y texto permanecen en JSON privados bajo `out/`.
- Artefactos: `haru audio.asr.{txt,json}` y `haru audio (1).asr.{txt,json}`.
  Generador: `spikes/full-duplex/transcribe_recordings.py`.

En el segundo archivo el STT reconoce la petición de hablar sobre videojuegos
y la continuación del modelo sobre IA; después de reiteraciones reconoce una
respuesta del modelo sobre videojuegos. En el primero reconoce solicitudes de
hablar español mientras el modelo continúa en inglés. Esto apoya comprensión
parcial y seguimiento deficiente, no la afirmación de que nunca recibe voz.

El STT contiene tramos dudosos, especialmente al final del primer archivo:
aparecen textos en otros idiomas y fórmulas de despedida que podrían ser
alucinaciones. No se usan para afirmar qué idioma habló la persona o el modelo.
Los tiempos son aproximados, no alineación forzada ni marcas de fin de voz.
Sin transcripción humana no se calcula WER y no se acredita METRICS §5.

No se encontró un error evidente de formato o presupuesto de cómputo. Haru es
base y su personaje predeterminado favorece temas tecnológicos; ambas cosas
pueden contribuir al mal seguimiento, sin probar causalidad. La referencia
inglesa compartida puede influir en español; tampoco se ha aislado su efecto.
El códec reconstruido sigue pendiente de escucha comparativa. No se declara
que el problema sea inevitable en todos los usos de Haru ni que esté resuelto.

## 10. Candidato considerado: Qwen3-Omni (ensayo cancelado)

Ivan eligió explícitamente priorizar conversación integrada EN/ES con
[Qwen3-Omni-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct).
La ficha declara entrada y salida hablada en ambos idiomas y voces incluidas
Ethan, Chelsie y Aiden, sin referencia personal. No se elige la variante Thinking,
que carece de salida de voz.

Se investigará la cuantización comunitaria
[cyankiwi AWQ 4 bit](https://huggingface.co/cyankiwi/Qwen3-Omni-30B-A3B-Instruct-AWQ-4bit),
revisión `b8f7bfd32ec3e7a59fa78cad0be54463eb89e9a9`: seis shards,
27 551 508 922 bytes. La configuración usa `compressed-tensors`; Talker y
Code2Wav quedan excluidos de la cuantización. Su compatibilidad y calidad se
deben comprobar, no deducir del modelo original.

La API básica genera por intervenciones. El
[adaptador dúplex de vLLM-Omni](https://github.com/vllm-project/vllm-omni/blob/main/docs/serving/realtime_duplex_api.md)
gestiona entrada concurrente, VAD e interrupciones en el servidor; no equivale
a la política nativa de entrada/salida por frames de Haru. Este cambio de
prioridad no satisface automáticamente FD-03 ni adopta una arquitectura del
producto. Se probarán primero comprensión y voz con los componentes integrados,
después el transporte y sus tiempos, registrando por separado cada resultado.

Antes de ejecutarlo, Ivan cambió explícitamente su elección a Sophon-Realtime
4B Flash. Los pesos de Qwen llegaron a descargarse; se eliminó únicamente esa
copia regenerable para recuperar espacio para Sophon. Qwen no se cargó ni se
evaluó. Su entorno preliminar separado no modificó el entorno de Haru.

## 11. Sophon-Realtime 4B Flash

Elección explícita de Ivan: [pesos oficiales](https://huggingface.co/adventists-ai/Sophon-Realtime-4B-Flash)
y [código](https://github.com/adventists-ai/sophon-realtime/tree/ace091b1841adb2b0588cd609ac06e3dfc261643/flash).
Se prepara un ensayo exploratorio de escucha, seguimiento del tema y voz,
seguido de pausas e interrupciones. Español se considera experimental: la ficha
y las instrucciones documentan inglés/chino, no conversación española validada.

| Elemento | Configuración |
| --- | --- |
| Código | `ace091b1841adb2b0588cd609ac06e3dfc261643` |
| Pesos | `adventists-ai/Sophon-Realtime-4B-Flash`, `8597f03bcc95d02115b0657823784e8aab5bb737` |
| Tamaño publicado de archivos | 12 999 734 822 bytes, incluidas voces y metadatos |
| Entorno oficial | Python 3.12, vLLM 0.30.0, vLLM-Omni 0.30.0, duplexjev-vllm 0.3.0 |
| Perfil inicial | GPU de 24 GB, una sesión local, voz incluida Chelsie, inglés |
| Licencias declaradas | Apache-2.0 en código y pesos; NOTICE de los pesos enumera sus derivados |

Flash empaqueta DuplexJev-4B-Para con adaptador fusionado, una etapa de voz
derivada de Qwen3-TTS y su decodificador. Recibe audio directamente, sin STT
externo para responder, pero no es la variante E2E de la familia. El código
combina VAD de servidor con preguntas de toma de turno al propio modelo; al
hablar el usuario puede interrumpirse la reproducción. No se equipara sin
matices a generación simultánea nativa por frames.

El arranque oficial reserva aproximadamente 21 GB según sus autores. Sus
tiempos publicados corresponden a otro hardware y no se reportarán como
resultado local. Chelsie y Brand están incluidas; no hace falta clonar voz.
El modo Live añade gateway y ASR para transcripciones; la primera prueba usará
directamente `/v1/realtime` para no añadir esa dependencia a la respuesta.

La ruta de turnos del plugin solo define preguntas en `en` y `zh`; pasar `es`
directamente no es una configuración española validada. `serve_sophon.py`
añade alias `es` a las preguntas y plantilla inglesas, en memoria, sin modificar
upstream ni pesos. Permite conservar las preguntas inglesas y enviar `es` a la
etapa de voz, que sí contempla ese idioma, con instrucciones españolas. No
equivale a entrenar ni validar turnos españoles. No se acreditan FD-01–FD-03 ni
S01-CA-05 por instalar o calentar el servidor.

### Ejecución técnica y primeras intervenciones

- Descarga completa: nueve objetos LFS comprobados por tamaño y SHA-256 contra
  el Hub, incluidos pesos y voces. Evidencia local `data/full-duplex/sophon-verified.json`.
- Entorno separado: 265 paquetes compatibles según `uv pip check`; versiones
  resueltas en `spikes/full-duplex/requirements-sophon.txt`, sin alterar Haru.
  PyTorch 2.13.0+cu130; plugin Sophon 1.5.0 en la revisión de código fijada.
- Primer arranque 23:29–23:33 de Colombia: carga, compilación y calentamiento
  completos, `/health` sano. RTX 4090, MPS, 21 528 MiB de memoria global observada
  en esa GPU, incluido el escritorio; no es consumo exclusivo del modelo.
- Página propia en loopback: captura PCM float32 a 16 kHz, salida PCM16 a
  24 kHz por WebSocket. Voces incluidas, sin archivo de referencia personal.
  Sintaxis JS comprobada con `node --check`; captura física y escucha humana
  en esa página todavía pendientes.

Se reutilizaron fragmentos del canal del usuario de los WebM aportados, de una
sola persona y sin entrenamiento ni particiones: inglés desde 20 s durante
12 s; español desde 20 s durante 20 s; petición inglesa breve desde 28,9 s
durante 3,3945 s decodificados. Procedencia y hashes privados:
`out/sophon-inputs.json`. No constituyen un corpus de evaluación.

HTTP, una intervención por idioma, temperatura 0,7, top-p 0,9, semilla solicitada
20261120, voz `chelsie_en`, instrucciones de seguir el tema y contestar brevemente:

| Prueba | Solicitud → primer bloque recibido | Duración de voz producida | Resultado observado |
| --- | --- | --- | --- |
| Inglés, `language=en` | 270 ms | 5,92 s | Texto sobre vídeos, próximo a una repetición del usuario; seguimiento insuficiente para aceptar una charla |
| Español, `language=es` | 206 ms | 5,20 s | Texto español relativo a un saludo; no demuestra resolver correctamente toda la petición |

Audio finito en ambos casos. Whisper turbo local, con idioma forzado al del
ensayo, produjo texto compatible con el texto generado en ambos WAV. Esto
reduce la sospecha de un códec totalmente ininteligible, pero no sustituye
escucha humana ni acredita naturalidad o exactitud semántica. Artefactos:
`sophon-reply-en.{wav,json}`, `sophon-reply-es.{wav,json}` y
`sophon-asr-check.json` bajo `out/`. No se calculan WER ni percentiles con n=1.

WebSocket antes de la adaptación ES: un fragmento inglés breve, precedido por
1 s de silencio y seguido de silencio, enviado en bloques de 80 ms a velocidad
real. El STT reconoció la petición de hablar de videojuegos; el texto de
respuesta del modelo aceptó ese tema y preguntó qué quería saber. Se recibieron
seis bloques de voz, 5,039 s a 24 kHz, sin eventos de error. Primer bloque a los
5,202 s de iniciar la prueba, incluyendo silencio inicial y reproducción de la
entrada: no se reporta como latencia de respuesta. El log situó la liberación
de la respuesta especulativa a 884 ms de su inicio de silencio detectado.
Evidencia privada: `sophon-realtime-reply.{wav,json}`. Hubo STT diagnóstico en
la otra GPU durante este ensayo; no es un banco de rendimiento aislado.

Se reinició después con el adaptador ES. Las comprobaciones posteriores deben
identificarse por separado: los resultados anteriores no acreditan esa nueva
configuración ni su conversación española dúplex.

Configuración final con adaptación ES, calentada de nuevo:

- Español por WebSocket: entrada breve de 3,505 s, extraída desde 36,5 s del
  primer WebM. Whisper reconoce un saludo repetido, no la solicitud larga de
  cambiar de idioma; muestra por qué no deben usarse sus tiempos anteriores
  para recortar palabras sin revisar el contenido. El modelo devolvió un saludo
  español, cinco bloques y 2,182 s de audio; Whisper reconoció el mismo saludo.
  Sin eventos de error. Primer bloque a 5,726 s del inicio, incluyendo entrada
  y silencio inicial. Solo acredita la ruta española y un intercambio trivial.
- Inglés por WebSocket con el mismo `Origin` de la página: entrada breve de
  3,3945 s sobre videojuegos; respuesta textual que acepta ese tema y pregunta
  qué quiere saber, reconocida también por Whisper en la voz devuelta.
  Seis bloques, 4,64 s de audio, sin eventos de error. Primer bloque a 5,167 s
  del inicio, incluyendo entrada y silencio inicial. STT ejecutado después.
- Artefactos privados: `sophon-realtime-es.{wav,json}`,
  `sophon-realtime-en-final.{wav,json}`, `sophon-realtime-asr-check.json`.
  Origen y hashes de ambas entradas añadidos a `sophon-inputs.json`.
- `/health` sano; HTTP de la página comprobado. Comprobaciones finales:
  sintaxis Bash, `compileall`, `node --check`, `uv pip check`, rutas locales de
  enlaces Markdown y `git diff --check`. Prueba física del navegador,
  naturalidad, conversación española sostenida y barge-in humanos pendientes.

Interfaz y comandos: [SOPHON.md](../../spikes/full-duplex/SOPHON.md). Los números
de primer bloque son diagnósticos de ejecución; no satisfacen METRICS §7 ni
S01-CA-05. No se decide adoptar Sophon ni se cierra la selección del tutor.

## 12. Banco ampliado del 22 de noviembre

Se completaron 385 intervenciones sintéticas en las ejecuciones completas:
16 del piloto anterior/v2, 200 bilingües, 93 de política completa, 12 controles
de instrucciones, 56 escenarios de turnos y ocho del prompt breve. El intento
inicial de ocho turnos que falló al cambiar de sesión se conserva aparte.
También se ejecutaron STT posterior sobre 56 clips y la interfaz real con
micrófono simulado. No hubo STT externo en la conversación del modelo.

La política usa la rama `nicolas/s02-politica-tutor`, revisión
`a4e3a3fa83769051b453871ac8a66d8b54b9a76f`; no se modificó su contenido ni se
aprobaron sus decisiones pendientes. Los prompts completos y abreviados no
resolvieron consejo médico/legal, seguimiento y cierre. En español hubo
repetición considerable y respuestas fuera de tema. No se recomienda adoptar
las configuraciones probadas para el tutor.

Detalle, condiciones y pendientes en [SOPHON-RESULTADOS.md](SOPHON-RESULTADOS.md).
Agregado publicable sin audios: [SOPHON-2026-11-22.json](SOPHON-2026-11-22.json).
El [protocolo](SOPHON-PROTOCOLO.md) distingue latencia recibida/simulada de
audio audible, diagnósticos posteriores y evaluación humana. S01-CA-05 sigue
pendiente; no se modifica su casilla de aceptación.
