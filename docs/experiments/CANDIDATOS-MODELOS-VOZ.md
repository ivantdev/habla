# Candidatos de modelos para la ruta de voz (S05-P-02)

**Estado:** borrador para discutir con Ivan (C); **no hay decisión tomada**. **Responsable:** Nicolás (B), con Ivan (C); la elección se registra en ADR-004. **Bloquea:** G1 (un turno hablado real). **Spec:** [SPEC-05](../specs/SPEC-05-voice-conversation.md), pregunta S05-P-02.

La spec pide ASR, modelo de lenguaje, TTS y VAD **abiertos si resultan viables**, y que acceso a GPU, memoria y soporte real se prueben. Esta tabla reúne candidatos con los datos que hay que verificar antes de elegir; no sustituye las mediciones en las GPU.

**Fecha de consulta:** 2026-11-08. Las licencias y tamaños proceden de búsquedas web, en su mayoría de fuentes secundarias. **Antes de adoptar un modelo, confirma su licencia en el archivo `LICENSE` o la ficha oficial** (RT-01, RT-07 piden documentar licencias). Lo marcado «por verificar» no se comprobó.

## 1. Criterios de elección

| Criterio | Por qué importa |
| --- | --- |
| Inglés y habla conversacional de estudiantes con acento | El tutor habla en inglés y transcribe estudiantes de L2 (S05-RF-03, S05-RF-04) |
| Latencia | Un turno fluido; la interrupción ya se detiene en ~110 ms ([SPIKE-AUDIO](SPIKE-AUDIO.md)), el resto del turno debe acompañar |
| Memoria de GPU | El evaluador fonético comparte GPU en el PC de la demo (RNF-02, S05-CA-06); el LLM y el TTS no deben desplazarlo |
| Licencia | Documentada y compatible con el uso del proyecto (RT-01, RT-07) |
| Corre en CPU o en Mac | Permite desarrollar sin las GPU (16 GB en el Mac de Nicolás) |
| Salida a 22 050 Hz o conversión sencilla | El canal ya acepta la frecuencia nativa del TTS (`output_sample_rate_hz`, SPIKE-AUDIO §4) |

## 2. ASR

| Candidato | Licencia | Tamaño aprox. | Notas |
| --- | --- | --- | --- |
| Whisper `base` / `small` (vía `faster-whisper` o `whisper.cpp`) | MIT (modelos de OpenAI); licencia de `faster-whisper` por verificar | 74 M / 244 M de parámetros | Para desarrollar en el Mac con CPU o Metal. Calidad limitada con acento fuerte |
| Whisper `large-v3-turbo` | MIT | ~809 M de parámetros; la memoria de GPU varía según fuentes (de ~1,5 GB en int8 a ~6 GB), **por medir** | Candidato principal para las 5060. Multilingüe |
| Distil-Whisper `distil-large-v3` | MIT | ~756 M de parámetros | Solo inglés, más rápido que `large-v3`. Alternativa si la latencia es el cuello de botella |
| NVIDIA Parakeet TDT | Por verificar | Por verificar | Solo inglés. No encontré confirmación de licencia ni de soporte en el hardware del grupo |

Los modelos de Whisper cambian el texto que oye el tutor, pero **la evaluación de pronunciación no usa ASR** (queda fuera del alcance de SPEC-05, §4); el ASR solo debe dar una transcripción comprensible.

## 3. VAD

| Candidato | Licencia | Notas |
| --- | --- | --- |
| Energía (el del spike) | — | Provisional. **No sirve con parlantes** (8/10 falsas interrupciones con AEC, ver SPIKE-AUDIO §3). Útil con auriculares |
| Silero VAD | MIT según el paquete y el repositorio; algunos espejos muestran una etiqueta distinta, **verificar el `LICENSE` oficial** | Corre en CPU. Discrimina voz frente a ruido y sonido del tutor mejor que la energía; **no está comprobado** que resuelva el eco |
| WebRTC VAD | Por verificar | Ligero y clásico; menos robusto que Silero |

El eco con altavoces no se resuelve solo cambiando de VAD: hay que medirlo con la misma prueba de silencio (condiciones 4 a 6 del spike).

## 4. TTS

| Candidato | Licencia | Notas |
| --- | --- | --- |
| Piper (`en_US-lessac-medium`), el del spike | **El paquete `piper-tts` 1.x (OHF-Voice/piper1-gpl) figura como GPL-3.0**; el repositorio original (MIT) se archivó en octubre de 2025. Cada voz tiene además su propia licencia, **por verificar** | CPU, 22 050 Hz. Es lo que usa el spike (`piper-tts==1.8.0`). Hay que decidir si la licencia GPL es aceptable para el producto |
| Kokoro-82M | Pesos Apache 2.0; código MIT; depende de `espeak-ng`, que es GPL | 82 M de parámetros, ligero. Calidad de voz mejor que Piper según varias fuentes; **por comparar de oído** |
| Otros (XTTS, F5-TTS, etc.) | No verificado | Varios tienen pesos con restricciones no comerciales. Revisar antes de considerarlos |

Las referencias habladas de las cinco frases ancla (semana 2) salen del TTS elegido, y Ivan las revisa. Si el TTS cambia después, hay que regenerarlas.

## 5. Modelo de lenguaje del tutor

| Candidato | Licencia | Tamaño aprox. | Notas |
| --- | --- | --- | --- |
| Qwen3 4B, cuantizado a 4 bits | Apache 2.0 (según fuentes) | ~2,5 GB (estimación) | Para probar el flujo en el Mac |
| Qwen3 8B, Q4_K_M | Apache 2.0 (según fuentes) | ~5 GB | Cabe en una 5060 de 16 GB con espacio para ASR y TTS; en el Mac justo |
| Gemma 4 | Apache 2.0 (Gemma 1 a 3 usan los Gemma Terms of Use) | Por verificar | Lanzamiento reciente; **por verificar** que existan variantes pequeñas y su soporte en `llama.cpp` |
| Llama 3.1 8B Instruct | Llama 3.1 Community License (con atribución y política de uso aceptable) | ~5 GB en Q4 (estimación) | Descarga con aceptación en Hugging Face |

El tutor debe cumplir la política de RNF-08 (no corregir pronunciación, mantenerse en el tema y nivel); eso se comprueba con el corpus de casos, no con el tamaño del modelo.

## 6. Qué medir para decidir (en las 5060 y, si hace falta, en el PC de Ivan)

1. **Latencia del turno:** fin de la voz → primer audio del tutor, para cada combinación. Descomponer en ASR, primer token del LLM y primer fragmento de TTS.
2. **Memoria de GPU:** pico por modelo y conjunta, **con el evaluador fonético de Ivan cargado**.
3. **Calidad del ASR:** transcripción de las propias grabaciones del equipo (con acento de español), contando errores que cambien el sentido.
4. **Tutor:** el corpus de casos de RNF-08 (temas, solicitudes fuera de contexto, errores deliberados).
5. **TTS:** escucha comparada de las cinco frases ancla y de una respuesta larga.
6. **Eco:** repetir la prueba de silencio con parlantes y el VAD candidato.

## 7. Preguntas para Ivan

- ¿Cuánta memoria de GPU deja el evaluador fonético en su PC (4090 + 5090) para el resto de la ruta?
- ¿Aceptamos GPL-3.0 en el TTS (Piper), o se prefiere Kokoro por su licencia? ¿Qué exige RT-07 al documentar licencias?
- ¿Prefiere ASR de solo inglés (Distil-Whisper) o multilingüe (`large-v3-turbo`)?

## Fuentes consultadas

- [Piper TTS: lanzamiento 1.3.0 en OHF-Voice/piper1-gpl](https://newreleases.io/project/github/OHF-Voice/piper1-gpl/release/v1.3.0)
- [Ficha de Kokoro-82M en Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M)
- [Silero VAD en PyPI](https://pypi.org/project/silero-vad)
- [Whisper large-v3-turbo (nota de Simon Willison)](https://www.simonwillison.net/2024/Oct/1/whisper-large-v3-turbo-model)
- [Ficha de distil-large-v3](https://huggingface.co/distil-whisper/distil-large-v3/blob/main/README.md?code=true)
- [Qwen3 8B GGUF (LM Studio)](https://huggingface.co/lmstudio-community/Qwen3-8B-GGUF)
- [Términos de uso de Gemma](https://ai.google.dev/gemma/terms)
