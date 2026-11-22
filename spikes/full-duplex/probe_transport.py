"""Prueba WebSocket con señal sintética conocida; no evalúa conversación."""

import asyncio
import json
from pathlib import Path

import aiohttp
import numpy as np
import soundfile as sf
import sphn

REPO = Path(__file__).resolve().parents[2]


async def main():
    base = "http://127.0.0.1:8998"
    source, rate = sf.read(REPO / "data/full-duplex/reference/kokoro-HEARME.wav", dtype="float32")
    audio = np.concatenate([np.zeros(rate, dtype="float32"), source[:rate],
                            np.zeros(rate, dtype="float32")])
    audio = np.pad(audio, (0, (-len(audio)) % 3200))
    async with aiohttp.ClientSession() as client:
        async with client.get(base + "/api/ready") as response:
            assert (await response.json())["ready"]
        async with client.get(base + "/api/config") as response:
            config = await response.json()
        reference = config["default_references"]["es"]["id"]
        async with client.post(base + "/api/session", json={
            "system_prompt": "Eres una persona amable y conversas de viva voz en español.",
            "reference_audio_id": reference,
        }) as response:
            assert response.status == 200, await response.text()
            session_id = (await response.json())["id"]
        writer, reader = sphn.OpusStreamWriter(rate), sphn.OpusStreamReader(rate)
        samples = 0
        async with client.ws_connect(base + "/api/chat?session_id=" + session_id) as ws:
            for start in range(0, len(audio), 3200):
                pages = writer.append_pcm(audio[start:start + 3200])
                if pages:
                    await ws.send_bytes(b"\x01" + pages)
            async with asyncio.timeout(10):
                while samples < 2 * rate:
                    message = await ws.receive()
                    assert message.type == aiohttp.WSMsgType.BINARY, message
                    if message.data and message.data[0] == 1:
                        pcm = reader.append_bytes(message.data[1:])
                        if pcm is not None:
                            samples += pcm.shape[-1]
        result = {
            "test": "synthetic signal, sent in a burst; not conversation or latency",
            "session_id": session_id,
            "input_seconds": len(audio) / rate,
            "received_seconds_at_least": samples / rate,
            "input": "1s silence + 1s public synthetic speech + 1s silence, padded",
        }
        output = REPO / "spikes/full-duplex/out/websocket-probe.json"
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
