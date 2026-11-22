"""Ensayo WebSocket con una grabación enviada en tiempo real, sin altavoz."""

import argparse
import asyncio
import base64
import collections
import json
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import websockets


async def run(args):
    speech, rate = sf.read(args.wav, dtype="float32")
    if rate != 16000 or speech.ndim != 1:
        raise ValueError("Expected mono 16 kHz WAV")
    audio = np.concatenate([np.zeros(16000, np.float32), speech,
                            np.zeros(20 * 16000, np.float32)]).astype("<f4")
    chunks, text, errors = [], [], []
    events = collections.Counter()
    first, output_rate = None, 24000
    done = asyncio.Event()
    started = time.perf_counter()
    async with websockets.connect("ws://127.0.0.1:8000/v1/realtime", max_size=16 * 1024**2,
                                  origin="http://127.0.0.1:8999") as ws:
        await ws.send(json.dumps({"type": "session.update", "session": {
            "modalities": ["audio", "text"], "voice": "chelsie_en",
            "instructions": ("Listen to the user's chosen topic and answer in one short spoken sentence. "
                             + ("Speak only Spanish." if args.lang == "es" else "Speak English.")),
            "input_audio_format": "pcm_f32le", "output_audio_format": "pcm16",
            "turn_detection": {"type": "server_vad"},
            "extra_body": {"auto_response": True, "language": args.lang}}}))

        async def read():
            nonlocal first, output_rate
            async for raw in ws:
                ev = json.loads(raw)
                kind = ev.get("type", "")
                events[kind] += 1
                if kind in ["response.output_audio.delta", "response.audio.delta"]:
                    pcm = np.frombuffer(base64.b64decode(ev.get("delta") or ev["audio"]), dtype="<i2")
                    output_rate = ev.get("sample_rate_hz", 24000)
                    chunks.append(pcm)
                    if first is None:
                        first = time.perf_counter() - started
                if kind in ["response.output_text.delta", "response.audio_transcript.delta",
                            "response.output_audio_transcript.delta"]:
                    text.append(ev.get("delta", ""))
                if kind == "error":
                    errors.append(ev)
                    done.set()
                if kind == "response.done" and chunks:
                    done.set()

        reader = asyncio.create_task(read())
        try:
            for start in range(0, len(audio), 1280):
                if done.is_set():
                    break
                await ws.send(json.dumps({"type": "input_audio_buffer.append", "format": "pcm_f32le",
                                          "sample_rate_hz": 16000,
                                          "audio": base64.b64encode(audio[start:start + 1280].tobytes()).decode()}))
                await asyncio.sleep(0.08)
            if not done.is_set():
                await asyncio.wait_for(done.wait(), timeout=20)
            await ws.send(json.dumps({"type": "session.close"}))
        finally:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
    if errors:
        raise RuntimeError(errors)
    if not chunks:
        raise RuntimeError(f"No response audio; events={dict(events)}")
    pcm = np.concatenate(chunks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, pcm, output_rate, subtype="PCM_16")
    report = {"input": str(args.wav), "language": args.lang, "input_duration_s": len(speech) / rate,
              "input_rate": rate, "leading_silence_s": 1, "output_rate": output_rate,
              "output_duration_s": len(pcm) / output_rate, "first_chunk_after_connect_s": first,
              "total_s": time.perf_counter() - started, "text": "".join(text),
              "events": dict(events), "errors": errors,
              "limitation": "one streamed utterance; no audible playback; not formal response latency"}
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--lang", choices=["en", "es"], default="en")
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
