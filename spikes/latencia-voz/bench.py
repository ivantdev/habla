"""Banco de latencia de la ruta ASR -> LLM -> TTS (S05-P-02).

Simula una conversación turno a turno con modelos reales y mide cada tramo:
ASR final (t2-t1), primer token del LLM (t3-t2), primera frase (t4-t3) y
primer audio del TTS (t5-t4). La espera de silencio (t1-t0) es configuración
y el canal (t7-t5) se toma del spike de audio. Ver docs/experiments/LATENCIA-Y-CONTEXTO-VOZ.md.

Requiere llama-server y whisper-server ya arrancados (ver README.md).
"""
import argparse
import io
import json
import re
import statistics
import subprocess
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"

# Intervenciones de un estudiante B1 sobre el tema restaurante (texto fijo para
# sintetizar audio de prueba). Solo importa su duración, no su acento.
STUDENT_LINES = [
    "Hi, I'm fine, thank you.",
    "Yes, I like to eat out on weekends with my family.",
    "Last week I went to an Italian restaurant near my house and I ordered lasagna.",
    "I think the food was delicious but the service was a little slow.",
    "Not really, I usually cook at home because it is cheaper.",
    "My favorite dish is bandeja paisa, it has beans, rice, meat, egg and avocado.",
    "Sometimes I order takeaway when I am very tired after work.",
    "I would recommend it, but you need a reservation on Fridays.",
    "Yes, once they brought me the wrong dish and I had to wait again for my food.",
    "I prefer small restaurants because the atmosphere is more relaxed.",
]

SENTENCE_END = re.compile(r"[.!?](\s|$)")


def pct(values, q):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)


def gpu_memory():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True,
    ).stdout.strip()
    return out.splitlines()


# ---------- Prompt del tutor desde la política y las fichas ----------

def build_system_prompt(level="B1", topic="restaurant", phase="conversation"):
    pol = (REPO / "docs/content/POLITICA-TUTOR.md").read_text()
    template = re.search(r"### Prompt de sistema\n\n```text\n(.*?)```", pol, re.S).group(1)
    guidance = re.search(rf"\| {level} \|[^|]*\| `([^`]*)` \|", pol).group(1)
    phase_text = re.search(rf"\| `{phase}` \|[^|]*\| `([^`]*)` \|", pol).group(1)
    fichas = (REPO / "docs/content/FICHAS.md").read_text()
    ficha = json.loads(re.search(r"```json\n(.*?)```", fichas, re.S).group(1))
    assert ficha["id"] == topic
    obj = ficha["objectives_by_level"][level]
    return (template
            .replace("{level_guidance}", guidance)
            .replace("{topic_scenario}", obj["scenario_en"])
            .replace("{vocabulary}", ", ".join(obj["vocabulary"]))
            .replace("{structures}", ", ".join(obj["structures"]))
            .replace("{starter_questions}", " ".join(obj["starter_questions"]))
            .replace("{phase_instructions}", phase_text))


# ---------- Audio del estudiante ----------

def resample_16k(pcm: np.ndarray, sr: int) -> np.ndarray:
    n = int(len(pcm) * 16000 / sr)
    x = np.linspace(0, len(pcm) - 1, n)
    return np.interp(x, np.arange(len(pcm)), pcm.astype(np.float32)).astype(np.int16)


def make_student_audio(voice_path: Path):
    from piper import PiperVoice
    voice = PiperVoice.load(str(voice_path))
    clips = []
    for line in STUDENT_LINES:
        chunks = list(voice.synthesize(line))
        sr = chunks[0].sample_rate
        pcm = np.frombuffer(b"".join(c.audio_int16_bytes for c in chunks), dtype=np.int16)
        pcm16 = resample_16k(pcm, sr)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(pcm16.tobytes())
        clips.append({"text": line, "wav": buf.getvalue(), "seconds": round(len(pcm16) / 16000, 2)})
    return clips


# ---------- Etapas ----------

def asr(client, url, wav_bytes):
    t = time.perf_counter()
    r = client.post(f"{url}/inference",
                    files={"file": ("turno.wav", wav_bytes, "audio/wav")},
                    data={"language": "en", "temperature": "0.0", "response_format": "json"})
    r.raise_for_status()
    return r.json()["text"].strip(), (time.perf_counter() - t) * 1000


def llm(client, url, messages, cache_prompt, max_tokens):
    body = {
        "messages": messages,
        "stream": True,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "cache_prompt": cache_prompt,
        "chat_template_kwargs": {"enable_thinking": False},
        "stream_options": {"include_usage": True},
    }
    t = time.perf_counter()
    first_token = first_sentence = None
    text, timings, usage, finish = "", None, None, None
    with client.stream("POST", f"{url}/v1/chat/completions", json=body) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            ev = json.loads(line[6:])
            timings = ev.get("timings", timings)
            usage = ev.get("usage") or usage
            for ch in ev.get("choices", []):
                finish = ch.get("finish_reason") or finish
                piece = (ch.get("delta") or {}).get("content") or ""
                if not piece:
                    continue
                if first_token is None:
                    first_token = (time.perf_counter() - t) * 1000
                text += piece
                if first_sentence is None and SENTENCE_END.search(text.strip() + " "):
                    first_sentence = (time.perf_counter() - t) * 1000
    total = (time.perf_counter() - t) * 1000
    text = text.strip()
    m = SENTENCE_END.search(text + " ")
    sentence = text[: m.end()].strip() if m else text
    return {
        "text": text, "first_sentence_text": sentence,
        "ttft_ms": first_token, "first_sentence_ms": first_sentence or total, "total_ms": total,
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "completion_tokens": (usage or {}).get("completion_tokens"),
        "finish_reason": finish,
        "prompt_n": (timings or {}).get("prompt_n"),
        "prompt_ms": (timings or {}).get("prompt_ms"),
        "cache_n": (timings or {}).get("cache_n"),
        "predicted_per_second": (timings or {}).get("predicted_per_second"),
    }


class Piper:
    name = "piper-lessac-medium-cpu"

    def __init__(self, path):
        from piper import PiperVoice
        self.voice = PiperVoice.load(str(path))

    def first_audio_ms(self, text):
        t = time.perf_counter()
        next(iter(self.voice.synthesize(text)))
        return (time.perf_counter() - t) * 1000


class KokoroTTS:
    name = "kokoro-v1.0-onnx-cpu"

    def __init__(self, model, voices):
        from kokoro_onnx import Kokoro
        self.k = Kokoro(str(model), str(voices))

    def first_audio_ms(self, text):
        t = time.perf_counter()
        self.k.create(text, voice="af_heart", speed=1.0, lang="en-us")
        return (time.perf_counter() - t) * 1000


# ---------- Sesión ----------

def run_session(args, clips, tts_engines, cache_prompt):
    system = build_system_prompt()
    messages = [{"role": "system", "content": system}]
    turns = []
    with httpx.Client(timeout=120) as client:
        # Calentamiento: primera llamada de cada modelo fuera de la medición.
        asr(client, args.whisper_url, clips[0]["wav"])
        llm(client, args.llm_url, messages + [{"role": "user", "content": "Hello"}], False, 8)
        for e in tts_engines:
            e.first_audio_ms("Warm up.")

        for i in range(args.turns):
            clip = clips[i % len(clips)]
            text, asr_ms = asr(client, args.whisper_url, clip["wav"])
            messages.append({"role": "user", "content": text or "[inaudible]"})
            out = llm(client, args.llm_url, messages, cache_prompt, args.max_tokens)
            messages.append({"role": "assistant", "content": out["text"]})
            row = {
                "turn": i + 1, "audio_s": clip["seconds"], "asr_text": text, "asr_ms": round(asr_ms, 1),
                **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in out.items()
                   if k not in ("text", "first_sentence_text")},
                "first_sentence_text": out["first_sentence_text"],
            }
            for e in tts_engines:
                row[f"tts_ms_{e.name}"] = round(e.first_audio_ms(out["first_sentence_text"]), 1)
            turns.append(row)
            print(f"  [{'caché' if cache_prompt else 'sin caché'}] turno {i + 1:2d}: "
                  f"ctx={row['prompt_tokens']} asr={row['asr_ms']} ttft={row['ttft_ms']} "
                  f"frase={row['first_sentence_ms']}", flush=True)
    return turns


def summarize(turns, tts_names, hangover_ms, channel_ms):
    def col(key):
        return [t[key] for t in turns if t.get(key) is not None]

    rows = {}
    for label, key in [("ASR final (t2-t1)", "asr_ms"), ("Primer token (t3-t2)", "ttft_ms")]:
        rows[label] = col(key)
    rows["Primera frase (t4-t3)"] = [t["first_sentence_ms"] - t["ttft_ms"] for t in turns]
    for n in tts_names:
        rows[f"TTS primer audio, {n} (t5-t4)"] = col(f"tts_ms_{n}")
    for n in tts_names:
        rows[f"Total t7-t0 con {n}"] = [
            hangover_ms + t["asr_ms"] + t["first_sentence_ms"] + t[f"tts_ms_{n}"] + channel_ms for t in turns]
    return {k: {"p50": pct(v, .5), "p95": pct(v, .95), "max": round(max(v), 1), "n": len(v)} for k, v in rows.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm-url", default="http://127.0.0.1:8081")
    ap.add_argument("--whisper-url", default="http://127.0.0.1:8082")
    ap.add_argument("--models", type=Path, default=Path.home() / "modelos-habla/modelos")
    ap.add_argument("--turns", type=int, default=30)
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--hangover-ms", type=float, default=600)
    ap.add_argument("--channel-ms", type=float, default=85, help="t7-t5 medido en el spike de audio")
    ap.add_argument("--modes", default="cache,nocache")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    print("Generando audio del estudiante con Piper (voz ryan)...", flush=True)
    clips = make_student_audio(args.models / "en_US-ryan-medium.onnx")
    engines = [Piper(args.models / "en_US-lessac-medium.onnx"),
               KokoroTTS(args.models / "kokoro-v1.0.onnx", args.models / "voices-v1.0.bin")]
    names = [e.name for e in engines]

    result = {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": args.label, "args": {k: str(v) for k, v in vars(args).items()},
        "system_prompt_chars": len(build_system_prompt()),
        "audio_s": [c["seconds"] for c in clips], "sesiones": {}, "resumen": {},
    }
    for mode in args.modes.split(","):
        print(f"Sesión {mode}: {args.turns} turnos", flush=True)
        turns = run_session(args, clips, engines, cache_prompt=(mode == "cache"))
        result["sesiones"][mode] = turns
        result["resumen"][mode] = summarize(turns, names, args.hangover_ms, args.channel_ms)
    result["gpu_memoria"] = gpu_memory()

    path = OUT / f"bench-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nResultados en {path}\n")
    for mode, summ in result["resumen"].items():
        print(f"### {mode}\n\n| Tramo | p50 (ms) | p95 (ms) | máx (ms) | n |\n| --- | --- | --- | --- | --- |")
        for k, v in summ.items():
            print(f"| {k} | {v['p50']} | {v['p95']} | {v['max']} | {v['n']} |")
        print()
    print("Memoria GPU:", *result["gpu_memoria"], sep="\n  ")


if __name__ == "__main__":
    main()
