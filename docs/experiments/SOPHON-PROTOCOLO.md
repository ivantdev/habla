# Protocolo local de Sophon — 22 de noviembre de 2026

Ivan, SPEC-01: S01-RF-05 / S01-CA-05; RNF-01, RNF-08, RF-05.
Ensayo exploratorio reproducible, sin aceptación de producto.

## Configuración y datos

Modelo, revisiones y entorno: [registro de selección](FULL-DUPLEX.md#11-sophon-realtime-4b-flash).
RTX 4090 de 24 GB, una sesión activa, perfil oficial de tres etapas con MPS,
voz incluida `chelsie_en`, entrada PCM float32 mono 16 kHz, bloques de 80 ms,
salida PCM16 a 24 kHz. Muestreo por defecto del despliegue; sin semilla fijada.
Se conserva el JSON del plan antes de enviar el primer estímulo.

Datos generados con eSpeak NG, voz `en-us` o `es`, velocidad 165. Una voz por
idioma, sin hablantes humanos ni entrenamiento, validación y prueba por
hablante. El piloto sirve para ajustar el prompt; no se presenta como prueba
final independiente. Los WAV y trazas quedan en `spikes/full-duplex/out/`,
excluido de Git. No se publican los audios privados de Haru.

## Iniciativa y latencia técnica

1. Piloto: ocho respuestas breves del usuario, en el mismo orden, con prompt
   anterior y `sophon-conversation-v2-2026-11-22`. Se inspeccionan iniciativa,
   seguimiento, preguntas y datos inventados. No hay juez humano ciego.
2. Banco: 100 frases distintas por idioma, generadas con 20 temas × cinco
   plantillas del script. Una sesión continua por idioma, historial limitado
   por el plugin. No se reciclan diez grabaciones como cien ejemplos.
3. Se conservan fallos, turnos sin respuesta y anticipaciones. Tiempo límite:
   25 s después del fin de la entrada. No se recortan latencias negativas.
4. Se reportan p50, p95 y máximo desde el fin conocido del PCM sintético hasta
   el primer bloque recibido; aparte, hasta la primera señal de salida en
   una cola de reproducción simulada (40 ms de margen, amplitud > 0,005).
   Se registra también el retraso máximo de envío respecto al reloj previsto.

El emisor de archivos envía cada bloque al inicio de sus 80 ms; puede tener
hasta un bloque de ventaja frente a un micrófono que debe capturarlo primero.
Esta diferencia forma parte de los límites del banco, sin corregir números
después de medir ni equipararlos con la latencia del navegador.

Estas medidas no son «fin VAD humano → primer audio audible» de
[METRICS §7](METRICS.md#7-latencia-rnf-01). Tener cien entradas sintéticas no
satisface S01-CA-05 ni acredita calidad bilingüe. No se calculan intervalos
por hablante con una sola voz sintética ni se adopta 2 s como límite acordado.

Inspección acústica posterior, sin inferencias STT concurrentes durante los
bancos: Whisper large-v3-turbo local, revisión
`41f01f3fe87f28c78e2fbf8b568835947dd65ed9`, decodificación greedy, detección
automática de idioma. Selección fijada antes de escuchar: índices 0, 24, 49,
74 y 99 de cada idioma y las tres salidas de crisis TUT-15. Se compara el
texto reconocido con el texto generado, como diagnóstico de inteligibilidad;
no como naturalidad, comprensión del usuario ni evaluación humana.
Se comprueba además el audio de entrada de esos diez índices. Como diagnóstico
posterior a observar confusiones tempranas, se añaden las entradas EN 20
(`football`) y EN 30 (`cooking`); esas dos no son una muestra ciega.
Tras los primeros fallos del banco de políticas, se añade también la entrada
de la primera repetición de cada uno de sus 31 casos, como diagnóstico
exploratorio del estímulo. No se eliminan ni reemplazan intentos en función
de este STT posterior.

## Políticas del tutor

Fuente: rama `origin/nicolas/s02-politica-tutor`, revisión
`a4e3a3fa83769051b453871ac8a66d8b54b9a76f`, actualizada antes de medir.
Su [POLITICA-TUTOR.md](../content/POLITICA-TUTOR.md) coincide con la copia local.
Se usa su plantilla, niveles y ficha de restaurante; se añade una instrucción
experimental de iniciativa. No se modifica el módulo de Nicolás ni se dan
por aprobadas D-19, POL-10 o la ventana de cierre de POL-13.

El banco conserva IDs TUT/POL/CHK. Cada caso ejecutable se prueba por audio
en una sesión nueva, tres repeticiones, sin mezclar conversaciones previas.
En estos casos aislados se recibe la respuesta completa (`response.done`) y
se cierra la sesión, sin esperar a reproducirla. Los bancos de latencia y
turnos sí esperan la cola simulada, porque reutilizan el contexto o interrumpen
una respuesta en curso.
TUT-16 aislado usa un historial textual de crisis declarado en el plan. Se
añaden además tres sesiones de dos turnos de audio con crisis → petición de
continuar, para observar la transición con la respuesta real del modelo.
Se añaden peticiones ilegales y variantes de inyección directa, autoridad
fingida y petición de revelar instrucciones. Se inspecciona la respuesta
completa, no solo palabras como «sorry». La revisión textual del agente se
identifica como tal; no sustituye la anotación de Nicolás ni la escucha humana.

El silencio no equivale a enviar el texto `[inaudible]` de TUT-07. TUT-18
requiere una interrupción real del flujo y TUT-19 una sesión larga: se informan
por separado. La fase `closing` se proporciona como instrucción de sistema,
con historial textual declarado. Así se comprueba la despedida del modelo,
pero no el temporizador de SPEC-04, la transición a anclas ni la supresión
de nuevos turnos después del cierre; esas garantías requieren orquestación.

En el perfil tutor, POL-08 pide responder en inglés aunque la entrada sea
española. En el perfil libre bilingüe se permite español. Son configuraciones
distintas y sus resultados no se agregan como si fueran una sola política.

## Interfaz y turnos

Chromium con micrófono simulado: carga de instrucciones, envío exacto por
WebSocket, captura con energía, respuesta con audio programado, exportación
JSON y liberación del micrófono al terminar o fallar. Se comprueba también
permiso denegado. No acredita el micrófono físico del usuario ni su altavoz.

Pausas internas de 0,3 / 0,6 / 1 / 2 s en inglés y español, tres repeticiones
por condición. Interrupción explícita y asentimiento, tres repeticiones por
idioma. Se registra si hay salida antes del fin de la entrada y el tiempo
hasta el evento que ordena detener la reproducción. Este último no mide la
parada física del altavoz; el juicio de interrupción correcta queda separado.

La observación humana recibida el 22 de noviembre es negativa para la
configuración anterior en inglés: el usuario tiene que dirigir la charla.
No se dispone de exportación de la configuración exacta de esa sesión previa.
En una prueba posterior del mismo día, a las 12:49 de Bogotá, el usuario aportó
exportación del perfil tutor v1 e informó comprensión insuficiente. Se analiza
en [resultados](SOPHON-RESULTADOS.md#prueba-humana-posterior-comprensión-de-un-estudiante)
sin mezclarla con el banco sintético ni usar sus tiempos como VAD/altavoz formal.
No incluye audio del usuario ni transcripción de referencia. Español y la
evaluación estructurada con habla L2 siguen pendientes.

## Segundo ajuste exploratorio de prompt

Ante la repetición observada en v2, se añade `pilot-short`: los mismos ocho
estímulos, sesión nueva, instrucciones inglesas más breves, sin cambiar el
banco de cien turnos ya en ejecución. Es otro ajuste exploratorio, no una
prueba independiente ni una mejora asumida. Se conserva su prompt completo
en `plan.json` y en `bench_sophon.py` (`SHORT`). No sustituye la política v1.

También se fijan, tras observar fallos de la política completa, cuatro controles
de instrucciones (`instructions_sophon.py`), tres repeticiones cada uno:
responder una sola palabra, despedida con instrucciones cortas, consejo médico
y consejo legal con política abreviada. Se declaran como diagnóstico posterior,
no como prueba ciega ni sustitución de los 93 intentos originales.

## Comando de inspección STT posterior

En el equipo del ensayo, el entorno y los pesos Whisper ya estaban preparados
por el diagnóstico anterior. Sus dependencias resueltas están en
[requirements.txt](../../spikes/full-duplex/requirements.txt); no se activa ese
entorno para servir Sophon. Para recuperar los pesos si faltan:

```bash
data/full-duplex/venv/bin/python -c 'from huggingface_hub import snapshot_download; snapshot_download("openai/whisper-large-v3-turbo", revision="41f01f3fe87f28c78e2fbf8b568835947dd65ed9", local_dir="data/full-duplex/whisper-turbo")'
```

Con todos los bancos anteriores terminados, las rutas usadas en este ensayo son:

```bash
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 \
  XDG_CACHE_HOME="$PWD/data/full-duplex/cache" \
  data/full-duplex/venv/bin/python spikes/full-duplex/asr_sophon.py \
  --latency spikes/full-duplex/out/sophon-20261122-latency \
  --policy spikes/full-duplex/out/sophon-20261122-policy \
  --output spikes/full-duplex/out/sophon-20261122-asr.json
```

Esto transcribe muestras después del ensayo; no agrega STT a la conversación.
