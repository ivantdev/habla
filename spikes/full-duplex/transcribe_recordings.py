"""STT local de los dos canales de los WebM; salidas privadas en out/."""

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
MODEL = REPO / "data/full-duplex/whisper-turbo"


@torch.inference_mode()
def main():
    processor = WhisperProcessor.from_pretrained(MODEL, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(
        MODEL, dtype=torch.float16, local_files_only=True
    ).to("cuda").eval()
    timestamp_start = processor.tokenizer.convert_tokens_to_ids("<|0.00|>")
    language_ids = {value: key for key, value in model.generation_config.lang_to_id.items()}
    for source in sorted(OUT.glob("haru audio*.webm")):
        recording = {"file": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                     "asr": "openai/whisper-large-v3-turbo",
                     "revision": "41f01f3fe87f28c78e2fbf8b568835947dd65ed9",
                     "method": "20s independent windows, automatic language, greedy, no translation",
                     "channels": {}}
        rows = []
        for channel, speaker in [(0, "usuario"), (1, "modelo")]:
            raw = subprocess.run([
                "ffmpeg", "-v", "error", "-i", str(source), "-af", f"pan=mono|c0=c{channel}",
                "-ar", "16000", "-f", "f32le", "pipe:1",
            ], check=True, capture_output=True).stdout
            audio = np.frombuffer(raw, dtype="<f4").copy()
            windows = []
            for start in range(0, len(audio), 20 * 16000):
                clip = audio[start:start + 20 * 16000]
                offset, end = start / 16000, (start + len(clip)) / 16000
                inputs = processor(clip, sampling_rate=16000, return_tensors="pt",
                                   return_attention_mask=True).to("cuda")
                inputs["input_features"] = inputs["input_features"].to(torch.float16)
                generated = model.generate(**inputs, task="transcribe", return_timestamps=True,
                                           do_sample=False, num_beams=1, max_new_tokens=440)
                tokens = generated[0].tolist()
                languages = [language_ids[token] for token in tokens if token in language_ids]
                text = processor.tokenizer.decode(tokens, skip_special_tokens=True)
                window = {"start": offset, "end": end, "detected_language": languages[:1],
                          "text": text, "rms": float(np.sqrt(np.mean(clip ** 2)))}
                windows.append(window)
                segment_start, content = None, []
                for token in tokens:
                    if token >= timestamp_start:
                        position = min(end, offset + (token - timestamp_start) * 0.02)
                        if segment_start is not None and content:
                            segment_text = processor.tokenizer.decode(content, skip_special_tokens=True).strip()
                            if segment_text:
                                rows.append((segment_start, position, speaker, segment_text))
                        segment_start, content = position, []
                    else:
                        content.append(token)
                print(json.dumps({"file": source.name, "speaker": speaker, **window}, ensure_ascii=False), flush=True)
            recording["channels"][speaker] = {"channel": channel, "duration": len(audio)/16000,
                                               "windows": windows}
        destination = OUT / (source.stem + ".asr")
        destination.with_suffix(".asr.json").write_text(json.dumps(recording, ensure_ascii=False, indent=2) + "\n")
        lines = ["STT automático sin revisión humana. No es una transcripción de referencia.",
                 "Canal izquierdo: usuario; derecho: modelo. Tiempos aproximados; ventanas de 20 s.",
                 "Puede alucinar texto e idiomas con señal débil, silencio o voz ininteligible.", ""]
        lines += [f"[{start:06.2f}–{end:06.2f}] {speaker}: {text}"
                  for start, end, speaker, text in sorted(rows)]
        destination.with_suffix(".asr.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
