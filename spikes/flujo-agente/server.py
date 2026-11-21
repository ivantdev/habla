"""MVP desechable del flujo del agente de voz (S05). No es código de producto.

Une en una página la ruta completa: micrófono → fin de turno por energía → Whisper →
Qwen3 en streaming → Piper por frase → altavoz, y muestra la transcripción de ambos lados.
Es semidúplex: mientras el tutor habla, el audio del estudiante se descarta (sin interrupción).

Requiere llama-server (:8081) y whisper-server (:8082) arrancados (ver ../latencia-voz/README.md).
"""
import argparse
import asyncio
import io
import json
import re
import sys
import time
import wave
from pathlib import Path

import httpx
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "latencia-voz"))
from bench import build_system_prompt  # noqa: E402  prompt desde POLITICA-TUTOR.md y FICHAS.md

IN_RATE = 16_000  # el worklet entrega PCM s16le mono de 16 kHz en frames de 20 ms
FRAME_MS = 20
SENTENCE_END = re.compile(r"[.!?](\s|$)")
OPENING = "(The student has just joined the session. Greet them briefly and ask your first question.)"

ap = argparse.ArgumentParser()
ap.add_argument("--llm-url", default="http://127.0.0.1:8081")
ap.add_argument("--whisper-url", default="http://127.0.0.1:8082")
ap.add_argument("--voice", type=Path, default=Path.home() / "modelos-habla/modelos/en_US-lessac-medium.onnx")
ap.add_argument("--level", default="B1")
ap.add_argument("--topic", default="restaurant")
ap.add_argument("--rms", type=float, default=0.02, help="umbral de energía para considerar voz (0-1)")
ap.add_argument("--hangover-ms", type=int, default=600, help="silencio que cierra el turno")
ap.add_argument("--min-speech-ms", type=int, default=300, help="turnos más cortos se descartan")
ap.add_argument("--max-tokens", type=int, default=150)
ap.add_argument("--port", type=int, default=8000)
args = ap.parse_args()

from piper import PiperVoice  # noqa: E402

voice = PiperVoice.load(str(args.voice))
OUT_RATE = voice.config.sample_rate


def to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(IN_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def rms(frame: bytes) -> float:
    x = np.frombuffer(frame, dtype="<i2").astype(np.float32) / 32768
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0


def synthesize(text: str) -> bytes:
    return b"".join(c.audio_int16_bytes for c in voice.synthesize(text))


class Session:
    def __init__(self, ws: WebSocket, client: httpx.AsyncClient):
        self.ws = ws
        self.client = client
        self.messages = [{"role": "system", "content": build_system_prompt(args.level, args.topic)}]
        self.busy = False  # True desde el fin de turno hasta que el navegador termina de reproducir
        self.speech = bytearray()
        self.voiced_ms = 0
        self.silence_ms = 0
        self.pending = bytearray()

    async def event(self, type_, **payload):
        await self.ws.send_text(json.dumps({"type": type_, **payload}))

    async def state(self, value):
        await self.event("state", value=value)

    # ---------- Entrada del estudiante ----------

    async def on_audio(self, data: bytes):
        if self.busy:
            return
        self.pending += data
        frame_bytes = IN_RATE * FRAME_MS // 1000 * 2
        while len(self.pending) >= frame_bytes:
            frame, self.pending = bytes(self.pending[:frame_bytes]), self.pending[frame_bytes:]
            voiced = rms(frame) >= args.rms
            if not self.speech and not voiced:
                continue
            if not self.speech:
                await self.state("hablando")
            self.speech += frame
            if voiced:
                self.voiced_ms += FRAME_MS
                self.silence_ms = 0
            else:
                self.silence_ms += FRAME_MS
                if self.silence_ms >= args.hangover_ms:
                    await self.end_turn()
                    return

    async def end_turn(self):
        pcm, voiced = bytes(self.speech), self.voiced_ms
        self.speech, self.voiced_ms, self.silence_ms, self.pending = bytearray(), 0, 0, bytearray()
        if voiced < args.min_speech_ms:
            await self.state("escuchando")
            return
        self.busy = True
        asyncio.create_task(self.respond(pcm))

    # ---------- Turno del tutor ----------

    async def respond(self, pcm: bytes | None):
        timings = {}
        try:
            if pcm is None:
                user_text = OPENING
            else:
                await self.state("transcribiendo")
                t = time.perf_counter()
                r = await self.client.post(
                    f"{args.whisper_url}/inference",
                    files={"file": ("turno.wav", to_wav(pcm), "audio/wav")},
                    data={"language": "en", "temperature": "0.0", "response_format": "json"})
                r.raise_for_status()
                user_text = " ".join(r.json()["text"].split())
                timings["asr_ms"] = round((time.perf_counter() - t) * 1000)
                await self.event("student", text=user_text, audio_s=round(len(pcm) / 2 / IN_RATE, 1))
                if not user_text:
                    return
            self.messages.append({"role": "user", "content": user_text})
            await self.state("pensando")
            reply = await self.stream_tutor(timings)
            self.messages.append({"role": "assistant", "content": reply})
            await self.event("tutor_done", timings=timings)
        except Exception as e:  # el MVP muestra el error y sigue escuchando
            await self.event("error", message=f"{type(e).__name__}: {e}")
        finally:
            await self.event("playback_wait")  # el navegador responde playback_ended al vaciar su cola

    async def stream_tutor(self, timings) -> str:
        body = {
            "messages": self.messages, "stream": True, "max_tokens": args.max_tokens,
            "temperature": 0.7, "cache_prompt": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        t = time.perf_counter()
        text, spoken = "", 0
        await self.event("tutor_start")
        async with self.client.stream("POST", f"{args.llm_url}/v1/chat/completions", json=body) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                for ch in json.loads(line[6:]).get("choices", []):
                    piece = (ch.get("delta") or {}).get("content") or ""
                    if not piece:
                        continue
                    timings.setdefault("ttft_ms", round((time.perf_counter() - t) * 1000))
                    text += piece
                    await self.event("tutor_delta", text=piece)
                    # Cada frase completa se sintetiza en cuanto llega, sin esperar al resto.
                    while m := SENTENCE_END.search(text, spoken):
                        await self.speak(text[spoken:m.end()], timings, t)
                        spoken = m.end()
        await self.speak(text[spoken:], timings, t)
        return text.strip()

    async def speak(self, sentence, timings, t0):
        if not sentence.strip():
            return
        audio = await asyncio.to_thread(synthesize, sentence.strip())
        timings.setdefault("first_audio_ms", round((time.perf_counter() - t0) * 1000))
        await self.state("tutor")
        await self.ws.send_bytes(audio)


app = FastAPI()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    async with httpx.AsyncClient(timeout=120) as client:
        s = Session(ws, client)
        await s.event("config", sample_rate=OUT_RATE, level=args.level, topic=args.topic)
        s.busy = True
        asyncio.create_task(s.respond(None))  # el tutor abre la conversación
        try:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    await s.on_audio(msg["bytes"])
                elif json.loads(msg["text"]).get("type") == "playback_ended":
                    s.busy = False
                    await s.state("escuchando")
        except WebSocketDisconnect:
            pass


@app.get("/capture-worklet.js")
def worklet():  # mismo conversor a 16 kHz del spike de audio (S05-P-01)
    return FileResponse(HERE.parent / "audio-channel/static/capture-worklet.js", media_type="text/javascript")


app.mount("/", StaticFiles(directory=HERE / "static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=args.port)
