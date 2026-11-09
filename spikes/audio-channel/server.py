"""Spike desechable del canal de audio (S05-P-01, C-04). No es código de producto.

Valida la propuesta de C-04: negociación stream.open → stream.ready, frames binarios
con cabecera fija, audio del tutor organizado por generación e interrupción.
"""
import asyncio
import json
import struct
import time
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).parent
OUT_DIR = HERE / "out"
VOICE_PATH = OUT_DIR / "voices" / "en_US-lessac-medium.onnx"

# Orígenes de la página: servida por este backend (:8000) o por el proxy de desarrollo (:3000).
ALLOWED_ORIGINS = {
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
}

AUDIO_PROFILE_ID = "pcm16-v1"
IN_RATE = 16_000  # entrada: PCM s16le mono 16 kHz
OUT_RATE = 22_050  # salida: frecuencia nativa de la voz de Piper
FRAME_MS = 20
IN_FRAME_BYTES = IN_RATE * FRAME_MS // 1000 * 2  # 640
OUT_FRAME_BYTES = OUT_RATE * FRAME_MS // 1000 * 2  # 882

# Cabecera de frame, little-endian, 56 bytes:
# version u8 | kind u8 | reserved u16 | chunk_seq u32 | stream_id 16 B | turn_id 16 B | generation_id 16 B
HEADER = struct.Struct("<BBHI16s16s16s")
HEADER_VERSION = 1
KIND_STUDENT, KIND_TUTOR = 1, 2
NIL = uuid.UUID(int=0)

LEAD_MS = 200  # ventaja máxima del envío del tutor sobre el tiempo real
HEARTBEAT_MS, LEASE_MS = 5_000, 15_000  # valores de configuración; C-09 no usa lease

DEFAULT_TUTOR_TEXT = (
    "Hi! I'm your English tutor. Today we are going to talk about your weekend. "
    "What did you do on Saturday? Did you go anywhere special, or did you stay at home and relax? "
    "Tell me about the people you met, the food you ate and the places you visited. "
    "Take your time, there is no hurry. I'm listening."
)


def pack_header(kind, chunk_seq, stream_id, turn_id, generation_id):
    return HEADER.pack(
        HEADER_VERSION, kind, 0, chunk_seq, stream_id.bytes, turn_id.bytes, generation_id.bytes
    )


def unpack_header(data):
    version, kind, _reserved, chunk_seq, s, t, g = HEADER.unpack_from(data)
    return version, kind, chunk_seq, uuid.UUID(bytes=s), uuid.UUID(bytes=t), uuid.UUID(bytes=g)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


_voice = None


def load_voice():
    global _voice
    if _voice is None:
        if not VOICE_PATH.exists():
            raise SystemExit(
                f"Falta la voz de Piper en {VOICE_PATH}. Descárgala con (desde spikes/audio-channel):\n"
                "python -m piper.download_voices en_US-lessac-medium --download-dir out/voices"
            )
        from piper import PiperVoice

        _voice = PiperVoice.load(str(VOICE_PATH))
        assert _voice.config.sample_rate == OUT_RATE, _voice.config.sample_rate
    return _voice


def synthesize(text):
    """Genera bloques PCM s16le de OUT_RATE, uno por frase (Piper en CPU)."""
    for chunk in load_voice().synthesize(text):
        yield chunk.audio_int16_bytes


def dominant_hz(pcm):
    """Frecuencia de mayor energía del audio recibido; comprueba el remuestreo con un tono."""
    x = np.frombuffer(bytes(pcm), dtype="<i2").astype(np.float64)
    if len(x) < IN_RATE // 10:
        return None
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1 / IN_RATE)
    spectrum[freqs < 50] = 0
    return round(float(freqs[int(np.argmax(spectrum))]), 1)


@dataclass
class Generation:
    turn_id: uuid.UUID
    generation_id: uuid.UUID
    late_frames: int
    task: asyncio.Task = None
    chunk_seq: int = 0
    stop_at_seq: int = None  # al interrumpir: último frame (exclusivo) que aún se envía
    first_audio_ms: float = None


class Channel:
    def __init__(self, ws, practice_id):
        self.ws = ws
        self.practice_id = practice_id
        self.stream_id = None
        self.seq = 0
        self.lock = asyncio.Lock()
        self.pcm = bytearray()
        self.frames = 0
        self.next_chunk_seq = 0
        self.gaps = 0
        self.bad_frames = 0
        self.first_frame_t = None
        self.last_frame_t = None
        self.generation = None
        self.interrupts = []

    async def send_event(self, type_, payload):
        async with self.lock:
            self.seq += 1
            await self.ws.send_text(json.dumps({
                "v": 1,
                "event_id": str(uuid.uuid4()),
                "practice_id": self.practice_id,
                "stream_id": str(self.stream_id) if self.stream_id else None,
                "seq": self.seq,
                "occurred_at": now_iso(),
                "type": type_,
                "payload": payload,
            }))

    async def on_event(self, msg):
        """Procesa un mensaje de control. Devuelve False si hay que cerrar el canal."""
        type_, p = msg.get("type"), msg.get("payload") or {}
        if self.stream_id is None and type_ != "stream.open":
            await self.reject("STREAM_NOT_OPEN", "Primero hay que abrir el canal con stream.open.")
            return False
        if type_ == "stream.open":
            if p.get("audio_profile_id") != AUDIO_PROFILE_ID:
                await self.reject("UNSUPPORTED_AUDIO_PROFILE", "El perfil de audio no está soportado.")
                return False
            self.stream_id = uuid.uuid4()
            await self.send_event("stream.ready", {
                "stream_id": str(self.stream_id),
                "audio_profile_id": AUDIO_PROFILE_ID,
                "heartbeat_interval_ms": HEARTBEAT_MS,
                "lease_timeout_ms": LEASE_MS,
                "max_frame_bytes": HEADER.size + max(IN_FRAME_BYTES, OUT_FRAME_BYTES),
                "output_sample_rate_hz": OUT_RATE,
            })
        elif type_ == "spike.ping":
            await self.send_event("spike.pong", {"t_client": p.get("t_client")})
        elif type_ == "spike.tutor_say":
            self.start_generation(p.get("text") or DEFAULT_TUTOR_TEXT, int(p.get("late_frames", 0)))
        elif type_ == "student.speech_started":
            await self.interrupt(p)
        elif type_ == "spike.stats_request":
            await self.send_event("spike.stats", self.stats())
        # heartbeat y student.turn_ended no tienen efecto en el spike.
        return True

    async def reject(self, code, message):
        await self.send_event("stream.rejected", {
            "code": code,
            "message": message,
            "supported_profiles": [AUDIO_PROFILE_ID],
        })
        await self.ws.close(code=1008)

    def on_frame(self, data):
        now = time.perf_counter()
        if self.stream_id is None or len(data) != HEADER.size + IN_FRAME_BYTES:
            self.bad_frames += 1
            return
        version, kind, chunk_seq, stream_id, _turn_id, _gen = unpack_header(data)
        if version != HEADER_VERSION or kind != KIND_STUDENT or stream_id != self.stream_id:
            self.bad_frames += 1
            return
        if chunk_seq < self.next_chunk_seq:  # duplicado o desordenado: no se reescribe audio
            self.bad_frames += 1
            return
        if chunk_seq > self.next_chunk_seq:  # hueco: no se rellena con audio inventado
            self.gaps += 1
        self.next_chunk_seq = chunk_seq + 1
        self.frames += 1
        self.pcm += data[HEADER.size:]
        self.first_frame_t = self.first_frame_t or now
        self.last_frame_t = now

    def start_generation(self, text, late_frames):
        if self.generation and not self.generation.task.done():
            self.generation.task.cancel()
        gen = Generation(uuid.uuid4(), uuid.uuid4(), late_frames)
        gen.task = asyncio.create_task(self.speak(gen, text))
        self.generation = gen

    async def speak(self, gen, text):
        await self.send_event("tutor.audio_started", {
            "turn_id": str(gen.turn_id),
            "generation_id": str(gen.generation_id),
        })
        t0 = time.perf_counter()
        blocks = asyncio.Queue()

        async def produce():  # sintetiza la frase siguiente mientras se envía la actual
            it = synthesize(text)
            while (block := await asyncio.to_thread(next, it, None)) is not None:
                await blocks.put(block)
            await blocks.put(None)

        producer = asyncio.create_task(produce())
        start, sent_ms = None, 0.0
        try:
            while (block := await blocks.get()) is not None:
                if gen.first_audio_ms is None:
                    gen.first_audio_ms = round((time.perf_counter() - t0) * 1000, 1)
                for i in range(0, len(block), OUT_FRAME_BYTES):
                    if gen.stop_at_seq is not None and gen.chunk_seq >= gen.stop_at_seq:
                        return
                    start = start or time.perf_counter()
                    ahead_ms = sent_ms - (time.perf_counter() - start) * 1000
                    if ahead_ms > LEAD_MS:
                        await asyncio.sleep((ahead_ms - LEAD_MS) / 1000)
                    frame = block[i:i + OUT_FRAME_BYTES]
                    header = pack_header(KIND_TUTOR, gen.chunk_seq, self.stream_id, gen.turn_id, gen.generation_id)
                    async with self.lock:
                        await self.ws.send_bytes(header + frame)
                    gen.chunk_seq += 1
                    sent_ms += len(frame) / 2 / OUT_RATE * 1000
            await self.send_event("tutor.audio_ended", {
                "turn_id": str(gen.turn_id),
                "generation_id": str(gen.generation_id),
                "last_chunk_seq": gen.chunk_seq - 1,
            })
        finally:
            producer.cancel()

    async def interrupt(self, p):
        gen = self.generation
        record = {"turn_id": p.get("turn_id"), "client_offset_ms": p.get("client_offset_ms")}
        if gen and not gen.task.done() and gen.stop_at_seq is None:
            gen.stop_at_seq = gen.chunk_seq + gen.late_frames  # frames tardíos simulados
            same = p.get("interrupted_generation_id") == str(gen.generation_id)
            await self.send_event("tutor.interrupted", {
                "turn_id": str(gen.turn_id),
                "generation_id": str(gen.generation_id),
                "heard_until_ms": p.get("heard_until_ms") if same else None,
            })
            if gen.late_frames == 0:
                gen.task.cancel()
            record.update({
                "generation_id": str(gen.generation_id),
                "frames_sent_before": gen.chunk_seq,
                "late_frames": gen.late_frames,
                "tts_first_audio_ms": gen.first_audio_ms,
            })
        self.interrupts.append(record)

    def stats(self):
        audio_ms = len(self.pcm) / 2 / IN_RATE * 1000
        wall_ms = (self.last_frame_t - self.first_frame_t) * 1000 + FRAME_MS if self.frames else 0
        return {
            "frames": self.frames,
            "gaps": self.gaps,
            "bad_frames": self.bad_frames,
            "audio_ms": round(audio_ms, 1),
            "wall_ms": round(wall_ms, 1),
            "dominant_hz": dominant_hz(self.pcm),
            "interrupts": self.interrupts,
            "tts_first_audio_ms": self.generation.first_audio_ms if self.generation else None,
        }

    def close(self):
        if self.generation:
            self.generation.task.cancel()
        if self.frames:
            OUT_DIR.mkdir(exist_ok=True)
            path = OUT_DIR / f"recibido-{self.stream_id}.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(IN_RATE)
                w.writeframes(bytes(self.pcm))
            print(f"[spike] {path.name}: {json.dumps(self.stats())}")


app = FastAPI()


@app.websocket("/api/v1/practices/{practice_id}/stream")
async def stream(ws: WebSocket, practice_id: str):
    if ws.headers.get("origin") not in ALLOWED_ORIGINS:
        await ws.close(code=1008)  # antes de aceptar: el servidor responde 403 al handshake
        return
    await ws.accept()
    channel = Channel(ws, practice_id)
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                channel.on_frame(msg["bytes"])
            elif msg.get("text") is not None:
                if not await channel.on_event(json.loads(msg["text"])):
                    break
    finally:
        channel.close()


app.mount("/", StaticFiles(directory=HERE / "static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    t = time.perf_counter()
    load_voice()  # precarga: evita que la primera generación pague la carga del modelo
    print(f"[spike] voz cargada en {time.perf_counter() - t:.2f} s")
    uvicorn.run(app, host="127.0.0.1", port=8000)
