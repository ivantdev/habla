"""Inspección independiente del audio generado con Whisper local; no juicio humano."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "data/full-duplex/whisper-turbo"


@torch.inference_mode()
def run(args):
    rows = [json.loads(line) for line in (args.latency / "turns.jsonl").read_text().splitlines()]
    selected = [r for r in rows if int(r["id"].rsplit("-", 1)[1]) in [0, 24, 49, 74, 99]]
    sources = [(args.latency, r, "response") for r in selected]
    sources += [(args.latency, r, "stimulus") for r in rows if r in selected or r["id"] in ["v2-en-020", "v2-en-030"]]
    policy_rows = [json.loads(line) for line in (args.policy / "turns.jsonl").read_text().splitlines()]
    sources += [(args.policy, r, "response") for r in policy_rows if r["case"] == "TUT-15"]
    sources += [(args.policy, r, "stimulus") for r in policy_rows if r["repetition"] == 0]
    processor = WhisperProcessor.from_pretrained(MODEL, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL, dtype=torch.float16, local_files_only=True).to("cuda").eval()
    results = []
    for directory, row, kind in sources:
        filename = row["id"] if kind == "response" else hashlib.sha256((row.get("input_language", row["language"]) + row["input_text"]).encode()).hexdigest()[:16]
        wav = directory / "audio" / (filename + ".wav")
        if not wav.exists():
            results.append({"id": row["id"], "error": "No audio"})
            continue
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1"], capture_output=True, check=True).stdout
        audio = np.frombuffer(raw, dtype="<f4").copy()
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt", return_attention_mask=True).to("cuda")
        inputs["input_features"] = inputs["input_features"].to(torch.float16)
        tokens = model.generate(**inputs, task="transcribe", do_sample=False, max_new_tokens=350)
        result = {"id": row["id"], "kind": kind, "expected_text": row["text"] if kind == "response" else row["input_text"], "asr_text": processor.batch_decode(tokens, skip_special_tokens=True)[0], "audio_duration_s": len(audio) / 16000}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    args.output.write_text(json.dumps({"asr": "openai/whisper-large-v3-turbo", "revision": "41f01f3fe87f28c78e2fbf8b568835947dd65ed9", "decoding": "greedy, automatic language, no translation", "limitation": "Selected synthetic outputs, no human reference or naturalness score", "rows": results}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latency", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
