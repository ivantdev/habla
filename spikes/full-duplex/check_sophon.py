"""Prueba HTTP audio→voz de Sophon; no mide conversación dúplex ni latencia audible."""

import argparse
import base64
import io
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--lang", choices=["en", "es"], default="en")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    url = "http://127.0.0.1:8000"
    with urllib.request.urlopen(url + "/v1/models", timeout=10) as response:
        model = json.load(response)["data"][0]["id"]
    instructions = (
        "You hear the user directly. Follow their chosen topic and answer in one short spoken sentence. "
        "Do not transcribe or translate the question. No markdown. "
        + ("Speak only Spanish." if args.lang == "es" else "Speak English.")
    )
    payload = {"model": model, "stream": True, "modalities": ["text", "audio"],
               "language": args.lang, "voice": "chelsie_en", "max_tokens": 100,
               "temperature": 0.7, "top_p": 0.9, "seed": 20261120,
               "messages": [{"role": "system", "content": instructions},
                            {"role": "user", "content": [
                                {"type": "text", "text": "<|audio|>"},
                                {"type": "input_audio", "input_audio": {
                                    "data": base64.b64encode(args.wav.read_bytes()).decode(),
                                    "format": "wav"}}]}]}
    request = urllib.request.Request(url + "/v1/chat/completions",
                                    data=json.dumps(payload).encode(),
                                    headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    first = None
    chunks, chunk_times, text = [], [], ""
    with urllib.request.urlopen(request, timeout=180) as response:
        for line in response:
            if not line.startswith(b"data:"):
                continue
            raw = line[5:].strip()
            if raw == b"[DONE]":
                break
            event = json.loads(raw)
            if "error" in event:
                raise RuntimeError(event["error"])
            for choice in event.get("choices", []):
                content = (choice.get("delta") or {}).get("content")
                if not content:
                    continue
                if event.get("modality") == "audio":
                    audio, rate = sf.read(io.BytesIO(base64.b64decode(content)), dtype="float32")
                    if rate != 24000:
                        raise ValueError(f"Unexpected sample rate: {rate}")
                    at = time.perf_counter() - start
                    if first is None:
                        first = at
                    chunks.append(audio)
                    chunk_times.append(at)
                else:
                    text += content
    if not chunks:
        raise RuntimeError("No audio received")
    audio = np.concatenate(chunks)
    if not np.isfinite(audio).all():
        raise ValueError("Non-finite audio")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, audio, 24000)
    report = {"input": str(args.wav), "language": args.lang, "voice": "chelsie_en",
              "instructions": instructions, "seed": 20261120, "text": text,
              "request_to_first_chunk_s": first, "total_s": time.perf_counter() - start,
              "chunk_arrivals_s": chunk_times, "audio_duration_s": len(audio) / 24000,
              "rms": float(np.sqrt(np.mean(audio**2))), "finite": True,
              "limitation": "HTTP single utterance; not VAD-to-audible latency or a duplex test"}
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
