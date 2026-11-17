"""Transporte provisional de C-04 basado en el spike de audio."""

import asyncio
import struct
from uuid import UUID, uuid4

from .contracts import Count, DTO, Event, Identifier, StreamReady, utc_now
from .simulators import TUTOR_RATE


AUDIO_PROFILE = "pcm16-v1"
HEADER = struct.Struct("<BBHI16s16s16s")
STUDENT_BYTES = 640
TUTOR_BYTES = TUTOR_RATE // 50 * 2
MAX_FRAME_BYTES = HEADER.size + max(STUDENT_BYTES, TUTOR_BYTES)
ZERO_UUID = bytes(16)


class SpeechStart(DTO):
    turn_id: Identifier
    client_offset_ms: Count
    interrupted_generation_id: Identifier | None = None
    heard_until_ms: Count | None = None


class SpeechEnd(DTO):
    turn_id: Identifier
    last_chunk_seq: Count


class Channel:
    def __init__(self, practice_id: str, client_instance_id: str):
        self.id = str(uuid4())
        self.practice_id = practice_id
        self.client_instance_id = client_instance_id
        self._seq = 0
        self.client_seq = -1
        self.event_ids: dict[str, None] = {}
        self.outgoing: asyncio.Queue[dict | bytes | None] = asyncio.Queue(maxsize=128)
        self.closed = False

    def ready(self) -> dict:
        return StreamReady(
            stream_id=self.id, audio_profile_id=AUDIO_PROFILE, heartbeat_interval_ms=0,
            lease_timeout_ms=0, max_frame_bytes=MAX_FRAME_BYTES, output_sample_rate_hz=TUTOR_RATE,
        ).model_dump(mode="json")

    def event(self, kind: str, payload: dict) -> None:
        self._seq += 1
        self.send(Event(
            v=1, event_id=str(uuid4()), practice_id=self.practice_id, stream_id=self.id,
            seq=self._seq, occurred_at=utc_now(), type=kind, payload=payload,
        ).model_dump(mode="json"))

    def accept(self, event: Event) -> bool:
        if self.closed or event.practice_id != self.practice_id or event.stream_id != self.id:
            return False
        if event.seq <= self.client_seq or event.event_id in self.event_ids:
            return False
        self.client_seq = event.seq
        if len(self.event_ids) == 256:
            del self.event_ids[next(iter(self.event_ids))]
        self.event_ids[event.event_id] = None
        return True

    def send(self, item: dict | bytes) -> None:
        if self.closed:
            return
        if self.outgoing.full():
            self.finish()
            return
        self.outgoing.put_nowait(item)

    def finish(self) -> None:
        if self.closed:
            return
        self.closed = True
        if self.outgoing.full():
            while not self.outgoing.empty():
                self.outgoing.get_nowait()
        self.outgoing.put_nowait(None)


def student_frame(data: bytes, stream_id: str, turn_id: str) -> tuple[int, bytes] | None:
    if len(data) != HEADER.size + STUDENT_BYTES:
        return None
    version, kind, reserved, sequence, stream, turn, generation = HEADER.unpack_from(data)
    if (
        (version, kind, reserved) != (1, 1, 0) or stream != UUID(stream_id).bytes
        or turn != UUID(turn_id).bytes or generation != ZERO_UUID
    ):
        return None
    return sequence, data[HEADER.size:]


def tutor_frame(stream_id: str, turn_id: str, generation_id: str, sequence: int, pcm: bytes) -> bytes:
    return HEADER.pack(
        1, 2, 0, sequence, UUID(stream_id).bytes, UUID(turn_id).bytes, UUID(generation_id).bytes,
    ) + pcm
