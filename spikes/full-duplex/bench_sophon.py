"""Banco sintético local: tiempos de recepción/reproducción simulada, no altavoz."""

import argparse
import asyncio
import base64
import hashlib
import json
import platform
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
import websockets

ROOT = Path(__file__).resolve().parent
PROMPTS = json.loads((ROOT / "sophon-web/prompts.json").read_text())
RATE, FRAME = 16000, 1280
TOPICS = {
    "en": ["video games", "pizza", "music", "films", "football", "books", "cooking", "travel",
           "dogs", "cats", "photography", "gardening", "coffee", "cycling", "swimming", "chess",
           "drawing", "hiking", "learning English", "dancing"],
    "es": ["videojuegos", "pizza", "música", "películas", "fútbol", "libros", "cocina", "viajes",
           "perros", "gatos", "fotografía", "jardinería", "café", "ciclismo", "natación", "ajedrez",
           "dibujo", "senderismo", "aprender inglés", "baile"],
}
TEMPLATES = {
    "en": ["Let's talk about {}.", "What do you enjoy about {}?", "I know very little about {}.",
           "Can you give me a simple idea about {}?", "I would like to try something new about {}."],
    "es": ["Hablemos de {}.", "¿Qué te gusta de {}?", "Sé muy poco sobre {}.",
           "¿Puedes darme una idea sencilla sobre {}?", "Me gustaría probar algo nuevo sobre {}."],
}
PILOT = ["Hello.", "Minecraft.", "I usually build houses.", "Mostly with friends.",
         "I don't know.", "Let's talk about food instead.", "Pizza.", "Because it is quick."]
BASELINE = "Let's talk about video games. Follow the topic I choose, listen to my answers, and reply in one or two short sentences. Speak English."
SHORT = "You are a B1 English conversation partner. Lead a chat about video games; follow a new topic if I choose one. In each reply, acknowledge one detail I actually said and ask one specific follow-up question. If I say 'I don't know', give two concrete choices. Use at most two short sentences. Never invent my preferences. Avoid repeating yourself or asking 'What's on your mind?'. Do not correct my English. Plain spoken English only."


def speech(text, lang, directory):
    key = hashlib.sha256((lang + text).encode()).hexdigest()[:16]
    target = directory / f"{key}.wav"
    if not target.exists():
        raw = directory / f"{key}-raw.wav"
        subprocess.run(["espeak-ng", "-v", "en-us" if lang == "en" else "es", "-s", "165",
                        "-w", str(raw), text], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ar", str(RATE),
                        "-ac", "1", str(target)], check=True)
        raw.unlink()
        audio, _ = sf.read(target, dtype="float32")
        active = np.flatnonzero(np.abs(audio) > 0.005)
        if not len(active):
            raise ValueError("Synthetic stimulus is silent")
        sf.write(target, audio[max(0, active[0] - 160):active[-1] + 1], RATE)
    return sf.read(target, dtype="float32")[0]


class Session:
    def __init__(self, lang, instructions, directory, history=None):
        self.lang, self.instructions, self.directory = lang, instructions, directory
        self.record = None
        self.queue_end = 0
        self.closed = asyncio.Event()
        self.history = history or []

    async def __aenter__(self):
        self.ws = await websockets.connect("ws://127.0.0.1:8000/v1/realtime", max_size=16 * 1024**2,
                                            origin="http://127.0.0.1:8999")
        await self.ws.send(json.dumps({"type": "session.update", "session": {
            "modalities": ["audio", "text"], "voice": "chelsie_en", "instructions": self.instructions,
            "input_audio_format": "pcm_f32le", "output_audio_format": "pcm16",
            "turn_detection": {"type": "server_vad"},
            "extra_body": {"auto_response": True, "language": self.lang, "history": self.history}}}))
        while True:
            event = json.loads(await asyncio.wait_for(self.ws.recv(), 20))
            if event["type"] == "error":
                raise RuntimeError(event)
            if event["type"] == "session.updated":
                break
        self.reader = asyncio.create_task(self.read())
        return self

    async def __aexit__(self, *args):
        await self.ws.send(json.dumps({"type": "session.close"}))
        await asyncio.wait_for(self.closed.wait(), 20)
        await self.ws.close()
        self.reader.cancel()
        await asyncio.gather(self.reader, return_exceptions=True)

    async def read(self):
        async for raw in self.ws:
            ev = json.loads(raw)
            r, now, kind = self.record, time.perf_counter(), ev.get("type")
            if kind == "session.closed":
                self.closed.set()
            if r is None:
                continue
            r["events"][kind] += 1
            if kind == "error":
                r["errors"].append(ev)
            if kind in ["input_audio_buffer.speech_started", "output_audio_buffer.cleared"]:
                self.queue_end = now
                if r.get("interruption_at") and r.get("stop_event_ms") is None:
                    r["stop_event_ms"] = (now - r["interruption_at"]) * 1000
            if kind in ["response.output_audio.delta", "response.audio.delta"]:
                pcm = np.frombuffer(base64.b64decode(ev.get("delta") or ev["audio"]), dtype="<i2")
                rate = ev.get("sample_rate_hz", 24000)
                if rate != 24000:
                    r["errors"].append({"unexpected_output_rate": rate})
                self.queue_end = max(self.queue_end, now + 0.04)
                voiced = np.flatnonzero(np.abs(pcm.astype(np.int32)) > 164)
                if r["first_chunk_at"] is None:
                    r["first_chunk_at"] = now
                if len(voiced) and r["first_signal_at"] is None:
                    r["first_signal_at"] = self.queue_end + voiced[0] / rate
                self.queue_end += len(pcm) / rate
                r["audio"].append(pcm)
            if kind in ["response.output_audio_transcript.delta", "response.output_text.delta"]:
                r["text"] += ev.get("delta", "")
                if r["response_texts"]:
                    r["response_texts"][-1] += ev.get("delta", "")
            if kind == "response.created":
                r["done_at"] = None
                r["response_texts"].append("")
            if kind == "response.done" and ev.get("response", {}).get("status") != "cancelled":
                r["done_at"] = now

    async def turn(self, ident, text, audio=None, interruption=None, wait_playback=True):
        audio = speech(text, self.lang, self.directory) if audio is None else audio
        r = {"id": ident, "language": self.lang, "input_text": text, "input_duration_s": len(audio) / RATE,
             "text": "", "response_texts": [], "events": Counter(), "errors": [], "audio": [], "first_chunk_at": None,
             "first_signal_at": None, "done_at": None, "stop_event_ms": None}
        r["max_send_lateness_ms"] = 0
        self.record = r
        samples = np.concatenate([np.zeros(FRAME * 3, np.float32), audio])
        start = time.perf_counter()
        source_end = start + len(samples) / RATE
        sent, interrupted = 0, False
        while True:
            now = time.perf_counter()
            if interruption is not None and not interrupted and r["first_signal_at"] is not None and now >= r["first_signal_at"] + 0.5:
                samples = speech(interruption, self.lang, self.directory)
                sent, start = 0, now
                source_end = start + len(samples) / RATE
                r["interruption_at"], r["done_at"], interrupted = now, None, True
            if r["errors"] or now - source_end > 25:
                break
            drain_end = self.queue_end + 0.3 if wait_playback else (r["done_at"] or now) + 0.05
            if r["done_at"] and sent >= len(samples) and now > max(drain_end, source_end + 0.3):
                if interruption is None or interrupted:
                    break
            await asyncio.sleep(max(0, start + sent / RATE - time.perf_counter()))
            r["max_send_lateness_ms"] = max(r["max_send_lateness_ms"], (time.perf_counter() - start - sent / RATE) * 1000)
            frame = samples[sent:sent + FRAME] if sent < len(samples) else np.zeros(FRAME, np.float32)
            if len(frame) < FRAME:
                frame = np.pad(frame, (0, FRAME - len(frame)))
            await self.ws.send(json.dumps({"type": "input_audio_buffer.append", "format": "pcm_f32le",
                                          "sample_rate_hz": RATE,
                                          "audio": base64.b64encode(frame.astype("<f4").tobytes()).decode()}))
            sent += FRAME
        if not r["done_at"]:
            r["errors"].append({"timeout": True})
        if r["audio"]:
            sf.write(self.directory / (ident + ".wav"), np.concatenate(r.pop("audio")), 24000, subtype="PCM_16")
        else:
            r.pop("audio")
        if interruption is None:
            r["end_to_first_chunk_ms"] = None if r["first_chunk_at"] is None else (r["first_chunk_at"] - source_end) * 1000
            r["end_to_simulated_signal_ms"] = None if r["first_signal_at"] is None else (r["first_signal_at"] - source_end) * 1000
        r["elapsed_s"] = time.perf_counter() - start
        return r


async def main(args):
    directory = args.output
    directory.mkdir(parents=True, exist_ok=False)
    inputs = directory / "audio"
    inputs.mkdir()
    plan = {"created_at": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
            "prompt_version": "sophon-short-v1-20261122" if args.mode == "pilot-short" else PROMPTS["version"],
            "prompts": PROMPTS, "baseline": BASELINE,
            "short_prompt": SHORT,
            "rate": RATE, "frame_samples": FRAME, "synthesizer": subprocess.check_output(["espeak-ng", "--version"], text=True).strip(),
            "hardware": subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv"], text=True),
            "platform": platform.platform(), "definition": "known synthetic PCM end to received chunk / simulated playback, no browser or speaker",
            "repetition_policy": ("8 fixed utterances per profile; exploratory pilot" if args.mode.startswith("pilot") else
                                  "100 distinct sentences per language, one synthetic voice; not 100 independent speakers"),
            "topics": TOPICS, "templates": TEMPLATES, "pilot_inputs": PILOT}
    (directory / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    if args.mode == "pilot":
        tasks = [("baseline", "en", BASELINE, PILOT), ("v2", "en", PROMPTS["en"], PILOT)]
    elif args.mode == "pilot-short":
        tasks = [("short", "en", SHORT, PILOT)]
    else:
        tasks = [("v2", lang, PROMPTS[lang], [template.format(topic) for topic in TOPICS[lang] for template in TEMPLATES[lang]])
                 for lang in ["en", "es"]]
    with (directory / "turns.jsonl").open("w") as output:
        for profile, lang, instructions, texts in tasks:
            # Prepare all audio before timing the first turn.
            for text in texts:
                speech(text, lang, inputs)
            async with Session(lang, instructions, inputs) as session:
                for i, text in enumerate(texts):
                    row = await session.turn(f"{profile}-{lang}-{i:03d}", text)
                    row["profile"] = profile
                    output.write(json.dumps(row, ensure_ascii=False) + "\n")
                    output.flush()
                    print(json.dumps({k: row.get(k) for k in ["id", "text", "end_to_first_chunk_ms", "errors"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["pilot", "pilot-short", "latency"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
