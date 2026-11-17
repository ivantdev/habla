import asyncio
import sqlite3
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from .channel import AUDIO_PROFILE, Channel, SpeechEnd, SpeechStart
from .config import LOCAL_ORIGINS
from .contracts import Event, StreamOpen, utc_now
from .errors import PlatformError
from .orchestration import Orchestrator


async def _reject(socket: WebSocket, practice_id: str, code: str, message: str) -> None:
    await socket.send_json(Event(
        v=1, event_id=str(uuid4()), practice_id=practice_id, stream_id=None, seq=1, occurred_at=utc_now(),
        type="stream.rejected", payload={"code": code, "message": message, "supported_profiles": [AUDIO_PROFILE]},
    ).model_dump(mode="json"))
    await socket.close(code=1008)


async def _write(socket: WebSocket, channel: Channel) -> None:
    while True:
        message = await channel.outgoing.get()
        if message is None:
            await socket.close()
            return
        if isinstance(message, bytes):
            await socket.send_bytes(message)
        else:
            await socket.send_json(message)


async def _read(socket: WebSocket, channel: Channel, orchestrator: Orchestrator) -> None:
    while True:
        message = await socket.receive()
        if message["type"] == "websocket.disconnect":
            return
        if (frame := message.get("bytes")) is not None:
            orchestrator.receive_audio(channel, frame)
            continue
        data = message.get("text", "")
        if len(data) > 4096:
            continue
        try:
            event = Event.model_validate_json(data)
            if channel.accept(event):
                if event.type == "student.speech_started":
                    orchestrator.speech_start(channel, SpeechStart.model_validate(event.payload))
                elif event.type == "student.turn_ended":
                    orchestrator.speech_end(channel, SpeechEnd.model_validate(event.payload))
        except ValidationError:
            continue


async def serve_stream(socket: WebSocket, practice_id: str, orchestrator: Orchestrator) -> None:
    if (
        socket.headers.get("origin") not in LOCAL_ORIGINS
        or socket.url.hostname not in {"localhost", "127.0.0.1"}
        or not 1 <= len(practice_id) <= 128
    ):
        await socket.close(code=1008)
        return
    channel = None
    tasks = []
    await socket.accept()
    try:
        async with asyncio.timeout(orchestrator.settings.upload_seconds):
            message = await socket.receive()
        if message["type"] == "websocket.disconnect":
            return
        raw = message.get("text", "")
        if len(raw) > 4096:
            raise ValueError("invalid hello")
        hello = Event.model_validate_json(raw)
        if hello.type != "stream.open" or hello.practice_id != practice_id or hello.stream_id is not None:
            raise ValueError("invalid hello")
        request = StreamOpen.model_validate(hello.payload)
        if request.audio_profile_id != AUDIO_PROFILE:
            await _reject(socket, practice_id, "UNSUPPORTED_AUDIO_PROFILE", "El perfil de audio no está soportado.")
            return
        channel = orchestrator.attach(practice_id, request.client_instance_id)
        channel.client_seq = hello.seq
        channel.event_ids[hello.event_id] = None
        tasks = [
            asyncio.create_task(_write(socket, channel)),
            asyncio.create_task(_read(socket, channel, orchestrator)),
        ]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (ValidationError, ValueError, TimeoutError):
        if channel is None:
            await _reject(socket, practice_id, "INVALID_STREAM_OPEN", "Abre el canal con una negociación válida.")
    except PlatformError as error:
        await _reject(socket, practice_id, error.code, error.message)
    except (WebSocketDisconnect, OSError, sqlite3.Error):
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if channel:
            orchestrator.detach(channel)
