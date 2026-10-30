# Requisitos de ¡Habla!

Estado: definición del MVP, versión 1.0; parámetros de prototipo identificados por separado.  
Fecha: 28 de octubre de 2026; actualizado el 30 de octubre de 2026 (D-12 a D-18).  
Alcance confirmado: MVP exclusivamente en inglés.

## 1. Objetivo

Permitir que un estudiante practique conversación en inglés con un tutor de voz sin interrupciones para corregirlo y reciba al finalizar observaciones sobre pronunciación, gramática y vocabulario, sustentadas en su sesión.

## 2. Fuentes y estado de las decisiones

- [Propuesta del proyecto](https://introsistemasinteligentes.com/proyectos/habla), consultada el 28 de octubre de 2026 mediante la [API pública utilizada por la página](https://introsistemasinteligentes.com/api/proyectos/habla).
- Decisiones del equipo recogidas en la entrevista: alcance, duración, contenido, cuentas, historial, interrupciones, conservación de audio, suficiencia de evidencia y recuperación ante fallos, detallados en este documento.
- Recursos y orientación técnica: equipos personales del grupo con GPU NVIDIA (un computador con RTX 4090 y RTX 5090 (Ivan) y otro con dos RTX 5060 de 16 GB (Nicolás)), preferencia por modelos de pesos abiertos y comparación del prototipo propio con una posible alternativa de Microsoft antes de seleccionar el motor fonético.
- Planificación del equipo del 30 de octubre de 2026: entrega en aproximadamente mes y medio con presentación tipo *Shark Tank*, primera iteración funcional en aproximadamente un mes, MVP ejecutado solo en local y despliegue en la nube aplazado a la iteración 2.
- Evaluación: datos públicos inicialmente, precisión objetivo mínima de 0,70 en validación y reporte de precisión y recall reales en prueba. Los límites de latencia se fijarán tras medir el prototipo.

**Confirmado** identifica decisiones expresas del equipo. **Base** identifica requisitos conservados de la propuesta original, compatibles con el MVP acordado. **Derivado** explicita una condición necesaria para cumplir ese alcance. **Pendiente** se reserva para parámetros o selecciones que requieren prototipado, preparación de contenido o verificación técnica; no incorpora funcionalidades adicionales al MVP.

## 3. Alcance

| Elemento | Estado | Definición |
| --- | --- | --- |
| Idioma | Confirmado | El MVP permite practicar inglés. |
| Tutor de voz | Confirmado | Conversación desde el micrófono del navegador, con respuestas habladas e interrupciones naturales: si el estudiante habla encima del tutor, este debe detenerse. |
| Evaluación | Confirmado | Informe al terminar, con pronunciación, gramática y vocabulario, sin nota global. Requiere las cinco frases ancla válidas. |
| Frases ancla | Confirmado | Las mismas cinco frases en todas las sesiones para facilitar la comparación; referencia estadounidense. Sus textos se definirán como contenido del producto. |
| Cuentas e historial | Confirmado | Registro con correo y contraseña, inicio y cierre de sesión; historial propio con fecha, tema, nivel, informe, audios vigentes y comparación por sonido en las frases ancla. Sin nota global. |
| Niveles y temas | Confirmado | A2, B1 o B2; restaurante, entrevista laboral, fin de semana, viajes o noticias; duración seleccionable de 5 o 10 minutos con paso automático a frases ancla. |
| Idioma de interfaz e informe | Confirmado | Español; conversación y frases ancla en inglés. |
| Audios conservados | Confirmado | Frases ancla y recortes de errores con consentimiento explícito durante 30 días. El usuario puede borrar sesiones, audios o cuenta. El audio completo y temporal se elimina al generar el informe, cancelar o dar por fallida la sesión. |
| Entorno de demo | Confirmado | Navegador de escritorio, ejecución local en un equipo del grupo con GPU NVIDIA y una única sesión de voz activa a la vez. Si está ocupado se informa al siguiente estudiante. Equipo y navegador de demo por documentar en el prototipo. El despliegue en la nube queda para la iteración 2 (D-13). |
| Motor de evaluación | Pendiente de experimento | Comparar un prototipo propio con la alternativa de Microsoft antes de elegir. No se considera obligatoria todavía una tecnología concreta. |
| Latencia | Pendiente de medición | Medir el prototipo antes de fijar límites de respuesta del tutor y generación del informe. |
| Evolución por sonido | Confirmado | Comparación entre sesiones sobre las mismas cinco frases ancla; sin mapa de vocales ni nota global. |
| Evaluación inicial | Confirmado | Datos públicos. Grabaciones de participantes, piloto longitudinal y comparación con monólogos quedan para una ampliación posterior. |
| Mapa de vocales | Fuera del MVP | Ampliación posterior. |
| Francés y alemán | Fuera del MVP | Posibles ampliaciones posteriores. |
| Certificación del nivel | Fuera del alcance | El producto no certifica niveles ni sirve para decisiones de admisión o contratación. |
| Verificación y recuperación de cuentas por correo | Fuera del MVP | No se incluyen en la demostración. |
| Reanudación tras recarga y varias conversaciones simultáneas | Fuera del MVP | La recuperación se limita a un reintento manual dentro de la sesión activa. |

## 4. Requisitos funcionales

| ID | Requisito | Criterio de aceptación | Estado |
| --- | --- | --- | --- |
| RF-01 | El sistema debe permitir seleccionar un nivel A2, B1 o B2 y uno de cinco temas predefinidos antes de iniciar una práctica de inglés. | Están disponibles restaurante, entrevista laboral, fin de semana, viajes y noticias; el tutor recibe tema y nivel al iniciar. Cada tema tiene objetivos de vocabulario y estructuras por nivel. | Confirmado |
| RF-02 | El sistema debe recibir la voz del estudiante mediante el micrófono del navegador. | Con permiso de micrófono concedido, la intervención del estudiante llega al procesamiento de la sesión. | Base |
| RF-03 | El sistema debe mantener una conversación mediante respuestas habladas del tutor. | Ante una intervención comprensible, el tutor responde en inglés de acuerdo con el tema y nivel configurados. | Base |
| RF-04 | El sistema debe mostrar la transcripción durante la conversación sin señalar errores. | Las intervenciones transcritas aparecen durante la sesión sin correcciones ni marcas de evaluación. | Base |
| RF-05 | El tutor debe reservar las correcciones para el informe final. | Durante la conversación no interrumpe para corregir ni solicita repetir para evaluar pronunciación. Si no comprende una intervención, puede pedir aclaración para mantener la charla. | Base |
| RF-06 | El sistema debe analizar la pronunciación a partir del audio del estudiante por una ruta independiente de la transcripción conversacional. | La evaluación utiliza evidencia acústica y no infiere los errores únicamente del texto transcrito. El motor y su salida fonética se decidirán tras comparar alternativas. | Base; motor pendiente de experimento |
| RF-07 | El sistema debe incluir una fase de lectura de las mismas cinco frases ancla al cerrar cada conversación. | Todas las sesiones presentan el mismo conjunto en inglés y cada grabación queda vinculada a su frase y sesión. Se ofrece una referencia hablada estadounidense. Los textos concretos son un entregable de contenido. | Confirmado |
| RF-08 | El sistema debe generar el informe al terminar una sesión con las cinco frases ancla válidas y procesamiento completado. | El informe en español presenta pronunciación, gramática y vocabulario con referencias a la sesión y sin nota global. Excluye de la evaluación fonética la conversación dudosa e indica qué no pudo evaluarse; no solicita repetirla. Si no hay observaciones respaldadas en una categoría, lo indica sin inventar errores. Una sesión incompleta no publica informe. | Confirmado |
| RF-09 | El sistema debe permitir comparar la pronunciación del estudiante con una referencia hablada. | El estudiante puede reproducir su audio y la referencia estadounidense del fragmento evaluado, incluidos los recortes de errores conservados con autorización. | Confirmado |
| RF-10 | El sistema debe recoger el consentimiento explícito para registrar voz y conservar frases ancla y recortes de errores de conversación. | Antes de grabar, el estudiante conoce los usos, audios conservados y plazo de 30 días y acepta explícitamente. El sistema registra su aceptación. Sin aceptación no se inicia la grabación. Si se elige un proveedor externo, el consentimiento debe explicar el envío de audio antes de habilitar esa ruta. | Confirmado; rechazo y proveedor derivados; desviación en la iteración 1 (D-18) |
| RF-11 | El sistema debe permitir crear una cuenta con correo y contraseña, iniciar sesión y cerrar sesión. | Una cuenta válida permite acceder al historial propio; credenciales inválidas se rechazan y cerrar sesión invalida el acceso autenticado. No se ofrece verificación por correo ni recuperación de contraseña en la demo. | Confirmado |
| RF-12 | El sistema debe ofrecer al estudiante un historial básico de sus sesiones. | El propietario autenticado puede ver fecha, tema, nivel, estado de la sesión, informe cuando exista y audios vigentes. Puede comparar resultados por sonido en las cinco frases ancla entre sesiones; no se presenta nota global. | Confirmado |
| RF-13 | El sistema debe permitir elegir una conversación de 5 o 10 minutos y pasar automáticamente a las frases ancla al alcanzar esa duración. | El tiempo de conversación se mide desde el inicio de la charla, incluyendo ambos interlocutores y las pausas; no incluye las frases ni la generación del informe. Al vencer, deja de abrir turnos y comienza el cierre. El estudiante puede cancelar antes; la sesión queda incompleta, sin informe, y se elimina el audio temporal. | Confirmado; cómputo de tiempo derivado |
| RF-14 | El sistema debe conservar recortes de errores de conversación autorizados y asociarlos a las observaciones del informe. | Cada recorte conserva el intervalo mínimo necesario para escuchar el error con contexto y se vincula con su observación y marca de tiempo. Puede reproducirse desde el historial mientras esté vigente. El tamaño máximo se definirá con el prototipo; no se conserva la conversación completa como recorte. | Confirmado; tamaño pendiente de prototipo |
| RF-15 | El tutor debe detener su respuesta hablada cuando el estudiante comience a hablar durante ella. | La reproducción se detiene y el sistema captura la nueva intervención del estudiante. El tiempo máximo de reacción y la gestión de la parte no escuchada se medirán y definirán con el prototipo. | Confirmado |
| RF-16 | El sistema debe permitir borrar sesiones, audios o la cuenta a solicitud del propietario. | El usuario autenticado puede eliminar una sesión y sus datos, audios individuales o su cuenta y sus datos asociados. La eliminación de un audio deja de ofrecer su reproducción en el informe. | Confirmado |
| RF-17 | El sistema debe permitir hasta dos reintentos por frase ancla no evaluable. | Cada frase tiene un intento inicial y como máximo dos repeticiones; no se repite una frase solo porque contiene errores. Para emitir informe se requieren las cinco frases válidas. Si una sigue sin poder evaluarse tras agotar los intentos, la sesión queda incompleta, sin informe, se elimina el audio temporal y se ofrece iniciar otra. | Confirmado |
| RF-18 | El sistema debe informar fallos de conexión o de modelos y permitir reintento manual. | Si el reintento falla, la sesión se marca incompleta, se elimina el audio temporal y se ofrece iniciar otra. Recargar no reanuda la sesión anterior. No se muestra una sesión fallida como completada. | Confirmado; desviación en la iteración 1 (D-17) |
| RF-19 | El sistema debe comprobar el acceso al micrófono antes de iniciar. | Si se deniega o no está disponible, muestra instrucciones para habilitarlo y permite volver a comprobarlo, sin iniciar una sesión de grabación. | Confirmado |
| RF-20 | El sistema debe comunicar el estado de los audios del historial. | Un audio vencido o eliminado no se ofrece como reproducible. Su ausencia no elimina el texto del informe mientras el usuario no borre la sesión o la cuenta. | Derivado |

## 5. Requisitos no funcionales

| ID | Categoría | Requisito y verificación | Estado |
| --- | --- | --- | --- |
| RNF-01 | Latencia | Medir el tiempo entre el fin de la intervención del estudiante y el comienzo de la respuesta audible, la reacción a interrupciones y la espera hasta el informe. Registrar percentiles y condiciones de prueba en escritorio, equipo local de demo con su GPU y una sesión activa. Fijar límites con los resultados antes de aceptar la demo. Los 2 segundos del percentil 95 de la propuesta son una referencia, no un límite acordado. | Medición confirmada; umbrales pendientes de prototipo |
| RNF-02 | Fluidez | La ruta de evaluación de pronunciación debe ejecutarse sin bloquear la ruta conversacional. Verificar que la conversación pueda continuar mientras exista análisis pendiente. | Base |
| RNF-03 | Calidad de detección | Seleccionar el umbral del motor en validación buscando una precisión de detección de errores fonéticos de al menos 0,70 y reportar el recall resultante. Informar precisión y recall reales en prueba por separado, con número de errores y fonemas evaluados. No ajustar con prueba ni garantizar que alcance la meta. Si no hay detecciones, la precisión no se considera una meta cumplida. | Confirmado |
| RNF-04 | Trazabilidad del informe | Toda observación de pronunciación debe referir a evidencia del motor de evaluación elegido; toda observación de gramática o vocabulario debe referir a una intervención transcrita. Revisar que el informe no introduzca ejemplos atribuidos al estudiante que no existan en la sesión. | Base |
| RNF-05 | Incertidumbre | Excluir de la evaluación fonética las palabras de conversación con transcripción dudosa, sin solicitar repetirlas. Identificar lo no evaluado sin considerarlo pronunciación correcta ni error. Definir el indicador de confianza y su umbral con el prototipo; las frases ancla usan texto conocido. | Confirmado; umbral pendiente de prototipo |
| RNF-06 | Criterio pedagógico | Señalar errores que cambien el significado o dificulten la comprensión, evitando tratar toda diferencia frente al acento de referencia como error. Falta definir la guía de anotación y revisión. | Base |
| RNF-07 | Privacidad | Conservar frases ancla y recortes autorizados por 30 días desde su grabación; permitir su eliminación anterior a solicitud del usuario. Eliminar audio completo y temporal al generar el informe, cancelar o dar por fallida la sesión. Mantener texto e informes hasta que el usuario los elimine. Verificar la caducidad y que los audios eliminados o vencidos ya no se sirvan. El plazo operativo para depurar archivos residuales se documentará en la implementación. | Confirmado; detalle operativo pendiente; excepción del corpus del equipo (D-16) |
| RNF-08 | Adecuación del tutor | El tutor debe seguir el contexto de la práctica y aplicar los límites temáticos de la propuesta: ajustarse a la ficha del tema, filtrar temas sensibles y no dar consejos médicos, legales ni emocionales. Falta definir los casos de evaluación y el comportamiento ante una solicitud fuera del contexto permitido. | Base |
| RNF-09 | Acceso y credenciales | Solo el propietario autenticado debe consultar, reproducir o eliminar sus sesiones, transcripciones, informes y audios. Guardar contraseñas mediante hash adaptativo con sal. Verificar que una segunda cuenta y una petición sin sesión no puedan acceder a datos de otra cuenta. | Derivado |
| RNF-10 | Capacidad | Admitir una única sesión de voz activa en el servidor. Si está ocupado, informar al siguiente estudiante y permitir reintentar sin comenzar una segunda conversación. Consultar el historial no equivale a iniciar una sesión de voz. | Derivado |
| RNF-11 | Comparabilidad | Comparar por sonido solo oportunidades evaluadas de las mismas frases y con condiciones de evaluación compatibles. Distinguir ausencia de evidencia de ausencia de errores; registrar versión de frases y evaluador para no atribuir cambios del motor al aprendizaje del estudiante. La visualización no constituye una nota global. | Derivado |
| RNF-12 | Usabilidad | Mostrar interfaz, estados de grabación, espera, fallos e informes en español; conversación y frases ancla en inglés. Los controles para iniciar, detener, repetir y cancelar deben tener etiquetas de texto comprensibles. | Idiomas confirmados; controles derivados |
| RNF-13 | Comunicación | Proteger las credenciales y el audio en tránsito al desplegar la demo en red; mantener las claves de proveedores en el servidor. Verificar que el navegador no reciba secretos de servicio. | Derivado |
| RNF-14 | Validez de muestras | Una frase válida contiene voz utilizable, corresponde al texto solicitado y permite evaluar su pronunciación con el motor seleccionado. Pronunciar con errores no invalida la muestra por sí solo. Calibrar en el prototipo la detección de silencio, audio truncado, ruido y cobertura del texto, documentando sus límites antes de aceptar la demo. | Suficiencia confirmada; criterios acústicos pendientes de prototipo |

## 6. Restricciones técnicas y evaluación del proyecto

Estas condiciones preservan la evaluación prevista en la propuesta y la adaptan a las decisiones del MVP. La selección de modelos y parámetros se resolverá mediante el prototipo.

Se priorizan modelos de pesos abiertos y una demostración local en equipos del grupo con GPU NVIDIA, navegador de escritorio y una sesión de voz activa a la vez. La API de Microsoft es una alternativa por investigar; no se ha confirmado que proporcione los fonemas, puntuaciones o características necesarios para la evaluación propuesta. La decisión entre el prototipo propio y el servicio externo queda aplazada hasta compararlos. La necesidad de conexión a internet y el presupuesto quedan pendientes.

| ID | Condición | Evidencia esperada | Estado |
| --- | --- | --- | --- |
| RT-01 | Usar una ruta conversacional con reconocimiento de voz, modelo de lenguaje y síntesis; la propuesta menciona Whisper. | Descripción del flujo y demostración de una sesión de voz. | Base |
| RT-02 | Comparar un prototipo propio con la alternativa de Microsoft antes de elegir el motor de evaluación de pronunciación. La propuesta original plantea wav2vec2, alineación y clasificador entrenado. | Comparación documentada de calidad de detección, latencia, costo, disponibilidad y salida necesaria para sustentar el informe. Verificar las capacidades reales y el acceso a la API. | Decisión de comparar confirmada; selección pendiente |
| RT-03 | Separar entrenamiento, validación y prueba por hablante. | Particiones documentadas sin hablantes compartidos; prueba reservada para la evaluación final. | Base |
| RT-04 | Comparar el prototipo propio y la alternativa de Microsoft sobre tareas equivalentes, incluyendo GOP como línea base donde sea aplicable. | Usar los mismos ejemplos y etiquetas para métricas comparables. Si un servicio solo ofrece puntuaciones agregadas o no permite evaluar los mismos errores, documentar la limitación y no equiparar esas puntuaciones con detección de errores por fonema. | Base adaptada; protocolo pendiente |
| RT-05 | Comparar el informe con un informe generado únicamente a partir de la transcripción. | Evaluación de observaciones sustentadas y errores atribuidos sin evidencia. | Base |
| RT-06 | Evaluar observaciones de gramática y vocabulario contra anotaciones humanas. | Precisión reportada por categoría; muestra y objetivo numérico pendientes. | Base |
| RT-07 | Evaluar inicialmente con datos públicos. L2-ARCTIC es el conjunto propuesto para detección fonética; valorar speechocean762 según compatibilidad con la tarea. | Documentar versión, licencia de uso, etiquetas, hablantes y particiones de cada conjunto. Reportar resultados por conjunto y las limitaciones de generalización. No exigir grabaciones propias para esta primera evaluación. | Datos públicos confirmados; selección concreta por verificar |

Las grabaciones de participantes, la comparación con monólogos y el piloto longitudinal de tres semanas quedan fuera de la evaluación inicial. No se afirmará eficacia pedagógica ni desempeño específico con acento colombiano a partir de pruebas exclusivamente con datos públicos.

### Contenido y recursos por preparar

- Cinco fichas temáticas, con objetivos de vocabulario y estructuras para A2, B1 y B2.
- Un conjunto fijo de cinco frases ancla, con identificadores estables y referencias habladas estadounidenses. Seleccionar sus textos para cubrir los sonidos que se pretende comparar.
- Casos de demostración para conversación, interrupción natural, informe sustentado, repetición de frases, historial, audio caducado y recuperación ante fallo.
- Una guía de evidencia válida y de anotación de errores. La referencia estadounidense no implica que una diferencia de acento comprensible constituya un error.

## 7. Decisiones y parámetros por completar

| ID | Decisión | Estado |
| --- | --- | --- |
| D-01 | Historial con fecha, tema, nivel, informes, audios vigentes y comparación por sonido; sin nota global ni mapa de vocales. | Resuelto |
| D-02 | A2/B1/B2; cinco temas definidos; elegir 5 o 10 minutos, paso automático a frases y cancelación anticipada. | Resuelto |
| D-03 | Cinco frases fijas, referencia estadounidense, interfaz e informes en español. | Resuelto; textos por preparar |
| D-04 | Audio autorizado durante 30 días y eliminación a solicitud; borrar audio completo y temporal al terminar, cancelar o fallar. | Resuelto; detalles de operación por implementar |
| D-05 | Pesos abiertos, posible API de Microsoft y GPU NVIDIA locales: un computador con RTX 4090 y RTX 5090 (Ivan) y otro con dos RTX 5060 de 16 GB (Nicolás). | Resuelto en orientación; presupuesto no definido |
| D-06 | Escritorio, ejecución local en un equipo del grupo y una sesión de voz activa; interrupciones naturales; aviso de servidor ocupado. | Resuelto; equipo y navegador de demo por documentar |
| D-07 | Cinco frases válidas, hasta dos reintentos por frase; omitir conversación dudosa. Ante fallo, reintento manual, sin reanudar tras recarga. | Resuelto; validez acústica por calibrar |
| D-08 | Medir prototipo antes de fijar límites de respuesta, interrupción y espera del informe. | Resuelto en estrategia; valores pendientes de medición |
| D-09 | Correo y contraseña sin verificación ni recuperación por correo en la demo. | Resuelto |
| D-10 | Datos públicos; precisión objetivo mínima de 0,70 en validación y reporte de precisión y recall reales en prueba; participantes para después. | Resuelto; protocolo por preparar |
| D-11 | Elegir entre prototipo propio y alternativa de Microsoft tras compararlos. | Resuelto en estrategia; selección pendiente de experimento |
| D-12 | Entrega en aproximadamente mes y medio desde el 30 de octubre de 2026, con presentación tipo *Shark Tank*; primera iteración funcional en aproximadamente un mes. | Resuelto; fechas exactas por confirmar |
| D-13 | Desarrollo y primera iteración solo en local; despliegue en la nube al final de la iteración 2, después del pitch. El acceso a la demo en el auditorio se decide en la revisión de G2, al cerrar la iteración 1. | Resuelto; acceso al auditorio pendiente (G2) |
| D-14 | Recorte en dos iteraciones y V3: versión local con usuario base; cuentas, acceso a la demo, borrado si alcanza y nube al final de la iteración 2; extras en V3. Los requisitos se conservan y el [plan por iteraciones](ROADMAP.md) fija cuándo se implementa cada uno. | Resuelto |
| D-15 | Criterios del pitch: 1 a 5, 7 y 8 de la sección 8, más el aislamiento entre cuentas del 6; el borrado y la caducidad del 6 se incluyen si alcanza el tiempo. Las cuentas son prioridad P0 de la iteración 2. | Resuelto |
| D-16 | Corpus interno del equipo: en la iteración 1 se conservan las sesiones de los tres integrantes (audio de conversación, transcripciones, informes, evidencia y anclas) para iterar el producto y medir RT-06 y WER, con su acuerdo escrito (D-18), fuera del repositorio y sin servirse por la API. Es una excepción a RNF-07 limitada al equipo; no es un estudio con participantes ni sustenta afirmaciones sobre acento colombiano. Falta decidir qué sesiones entran (¿también incompletas e intentos inválidos?), hasta cuándo se conservan y quién las borra a solicitud, en qué equipo viven y cómo se comparten, y si la recolección continúa para el equipo en la iteración 2. | Resuelto; alcance, plazo y ubicación pendientes |
| D-17 | Desviación aceptada de RF-18 en la iteración 1: cerrar el canal termina la práctica como incompleta y el reintento manual cubre fallos de modelo. El reintento ante corte de conexión y la idempotencia de subidas llegan en la iteración 2, con prioridad P0. | Resuelto; corrección en iteración 2 |
| D-18 | Desviación aceptada de RF-10 en la iteración 1: la app no muestra texto de consentimiento porque solo la usa el equipo con un usuario base (cuenta sembrada con `owner_id` constante), que tiene un consentimiento sembrado respaldado por el acuerdo escrito de los tres integrantes. El texto y el flujo de RF-10 llegan en la iteración 2 y describen la retención real. El usuario base se conserva en la iteración 2 y desde entonces inicia sesión como cualquier cuenta (RNF-09). | Resuelto; texto en iteración 2 |

### Trabajo de prototipo y preparación

| Pendiente | Resultado necesario | Referencias |
| --- | --- | --- |
| Selección del motor fonético | Comparación reproducible, capacidades verificadas de la alternativa de Microsoft y decisión documentada. Si no hay acceso a esa alternativa, registrar la limitación sin presentar una comparación inexistente. | RF-06, RT-02, RT-04 |
| Rendimiento y compatibilidad | Registrar modelo de GPU y memoria, modelos, navegador, red y carga; medir y fijar límites de respuesta, interrupción y generación del informe. | RF-15, RNF-01 |
| Evidencia acústica y confianza | Definir indicadores, umbrales y casos que distingan audio no evaluable de pronunciación con errores. | RF-17, RNF-05, RNF-14 |
| Gestión de audio | Definir el tamaño máximo de recortes y la depuración de archivos temporales, incluidos los abandonados por cierre del navegador o caída del servidor. No servir audios borrados o vencidos. | RF-14, RF-18, RNF-07 |
| Contenido | Preparar las cinco frases fijas, sus referencias y las fichas de los cinco temas para los tres niveles. | RF-01, RF-07 |
| Evaluación pública | Verificar datos, licencias y particiones; preparar protocolo, métricas y casos de informe. Evitar fugas por hablante y documentar las limitaciones de modelos preentrenados y servicios externos. | RNF-03, RT-03 a RT-07 |

La entrega y la primera iteración siguen D-12. El presupuesto de servicios externos se definirá durante la planificación. Las pruebas con participantes no son requisito de esta versión.

## 8. Criterios de aceptación de la demostración

1. Crear una cuenta, iniciar sesión y completar una práctica con nivel, tema y duración elegidos, usando voz y transcripción sin correcciones durante la charla.
2. Interrumpir al tutor hablando y comprobar que se detiene y recibe la nueva intervención, dentro del límite fijado tras medir el prototipo.
3. Pasar automáticamente a las cinco frases ancla y producir un informe solo después de obtener las cinco muestras válidas y completar el procesamiento.
4. Verificar una muestra inválida que se recupera mediante repetición y otra que agota el intento inicial y los dos reintentos: esta última debe finalizar incompleta, sin informe ni audio temporal conservado.
5. Consultar el informe y los audios vigentes desde el historial; comparar sonidos entre dos sesiones compatibles, sin nota global y sin tratar datos ausentes como aciertos.
6. Verificar eliminación de una sesión, un audio y una cuenta; comprobar caducidad de audios a los 30 días y ausencia de acceso desde otra cuenta.
7. Mostrar el tratamiento de micrófono denegado, servidor ocupado y fallo de conexión o modelo, sin presentar sesiones incompletas como finalizadas ni reanudarlas tras recargar.
8. Presentar las mediciones de rendimiento y calidad sobre datos públicos, incluyendo la meta de validación, los resultados reales en prueba y las limitaciones observadas. Documentar cualquier objetivo no alcanzado.
