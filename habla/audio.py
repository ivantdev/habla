"""Almacenamiento privado y limpieza de audio. SPEC-06, C-09 y D-16."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from sqlite3 import Connection
from uuid import uuid4
import json
import shutil
import wave

from .contracts import AnchorAttempt, AudioAsset, PhoneticResult, Practice, Report, Status, Turn, utc_now
from .errors import PlatformError, not_found
from .identity import ActorContext


INPUT_RATE = 16_000


@dataclass(frozen=True)
class Recording:
    asset: AudioAsset
    path: Path
    sample_rate: int


def wav_bytes(pcm: bytes, rate: int) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(pcm)
    return output.getvalue()


def decode_anchor(data: bytes, media_type: str, max_seconds: int) -> tuple[bytes, int]:
    if media_type not in {"audio/wav", "audio/wave", "audio/x-wav"}:
        raise PlatformError(415, "UNSUPPORTED_AUDIO_FORMAT", "Usa audio WAV PCM mono de 16 kHz.")
    if len(data) > max_seconds * INPUT_RATE * 2 + 4096:
        raise PlatformError(413, "AUDIO_TOO_LARGE", "La grabación excede el límite permitido.")
    try:
        with wave.open(BytesIO(data), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, INPUT_RATE):
                raise PlatformError(415, "UNSUPPORTED_AUDIO_FORMAT", "Usa audio WAV PCM mono de 16 kHz.")
            frames = audio.getnframes()
            if frames > max_seconds * INPUT_RATE:
                raise PlatformError(413, "AUDIO_TOO_LARGE", "La grabación excede el límite permitido.")
            pcm = audio.readframes(frames)
            if not frames or len(pcm) != frames * 2:
                raise wave.Error("truncated recording")
    except (wave.Error, EOFError) as error:
        raise PlatformError(422, "INVALID_AUDIO", "La grabación WAV está dañada o vacía.") from error
    return wav_bytes(pcm, INPUT_RATE), frames * 1000 // INPUT_RATE


class AudioStore:
    def __init__(self, db: Connection, data_dir: Path, actor: ActorContext):
        self.db = db
        self.actor = actor
        self.directory = data_dir / "audio"
        self.directory.mkdir(exist_ok=True)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS audio_assets (
                id TEXT PRIMARY KEY, practice_id TEXT NOT NULL REFERENCES practices(id),
                owner_id TEXT NOT NULL REFERENCES accounts(id), sample_rate INTEGER NOT NULL,
                data TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS audio_by_practice ON audio_assets(practice_id);
        """)

    def create(
        self, practice_id: str, source: str, sample_rate: int, data: bytes = b"", duration_ms: int = 0,
    ) -> Recording:
        asset = AudioAsset(
            id=str(uuid4()), practice_id=practice_id, source=source, captured_at=utc_now(),
            status="pending", media_type="audio/wav" if source == "anchor" else "application/octet-stream",
            duration_ms=duration_ms,
        )
        path = self._path(asset.id)
        try:
            path.write_bytes(data)
            with self.db:
                self.db.execute(
                    "INSERT INTO audio_assets VALUES (?, ?, ?, ?, ?)",
                    (asset.id, practice_id, self.actor.owner_id, sample_rate, asset.model_dump_json()),
                )
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return Recording(asset, path, sample_rate)

    def _path(self, asset_id: str) -> Path:
        return self.directory / f"{asset_id}.bin"

    def _recording(self, row) -> Recording:
        asset = AudioAsset.model_validate_json(row["data"])
        return Recording(asset, self._path(asset.id), row["sample_rate"])

    def get(self, asset_id: str) -> Recording:
        row = self.db.execute(
            "SELECT * FROM audio_assets WHERE id = ? AND owner_id = ?", (asset_id, self.actor.owner_id),
        ).fetchone()
        if row is None:
            raise not_found()
        return self._recording(row)

    def for_practice(self, practice_id: str) -> list[Recording]:
        rows = self.db.execute(
            "SELECT * FROM audio_assets WHERE practice_id = ? AND owner_id = ? ORDER BY rowid",
            (practice_id, self.actor.owner_id),
        )
        return [self._recording(row) for row in rows]

    def append(self, recording: Recording, pcm: bytes) -> None:
        with recording.path.open("ab") as output:
            output.write(pcm)

    def mark_available(self, recording: Recording, duration_ms: int) -> None:
        self._save(recording.asset.model_copy(update={"status": "available", "duration_ms": duration_ms}))

    def _save(self, asset: AudioAsset) -> None:
        with self.db:
            self.db.execute(
                "UPDATE audio_assets SET data = ? WHERE id = ? AND owner_id = ?",
                (asset.model_dump_json(), asset.id, self.actor.owner_id),
            )

    def discard(self, recording: Recording) -> None:
        recording.path.unlink(missing_ok=True)
        if recording.asset.status != "deleted":
            self._save(recording.asset.model_copy(update={"status": "deleted"}))

    def clean(self, practice_id: str, retain: set[str]) -> None:
        for recording in self.for_practice(practice_id):
            if recording.asset.id not in retain:
                self.discard(recording)

    def sweep_orphans(self) -> None:
        known = {self._path(row["id"]) for row in self.db.execute("SELECT id FROM audio_assets")}
        for path in self.directory.glob("*.bin"):
            if path not in known:
                path.unlink(missing_ok=True)

    def available_anchors(self, practice: Practice) -> list[Recording]:
        if practice.status != Status.COMPLETED or not practice.report_id:
            return []
        return [
            item for item in self.for_practice(practice.id)
            if item.asset.source == "anchor" and item.asset.status == "available" and item.path.is_file()
        ]


class Corpus:
    """Copia interna opcional. El servidor web nunca monta esta carpeta."""

    def __init__(self, directory: Path, member: str):
        self.root = directory / "corpus"
        self.member = member

    @staticmethod
    def _atomic_copy(source: Path, target: Path) -> None:
        temporary = target.with_suffix(".part")
        try:
            shutil.copyfile(source, temporary)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def copy_recording(self, recording: Recording) -> dict | None:
        asset = recording.asset
        directory = self.root / asset.practice_id / "audio"
        suffix = "wav" if asset.source == "anchor" else "pcm"
        target = directory / f"{asset.id}.{suffix}"
        if not target.is_file():
            if not recording.path.is_file():
                return None
            directory.mkdir(parents=True, exist_ok=True)
            self._atomic_copy(recording.path, target)
        metadata = asset.model_dump(mode="json")
        if suffix == "pcm":
            metadata["duration_ms"] = target.stat().st_size * 1000 // (2 * recording.sample_rate)
        return {**metadata, "file": f"audio/{target.name}", "sample_rate_hz": recording.sample_rate}

    def archive(
        self, practice: Practice, turns: list[Turn], attempts: list[AnchorAttempt],
        recordings: list[Recording], report: Report | None, evidence: list[PhoneticResult],
    ) -> None:
        directory = self.root / practice.id
        directory.mkdir(parents=True, exist_ok=True)
        manifest = {
            "member": self.member,
            "simulation": True,
            "practice": practice.model_dump(mode="json"),
            "transcript": [turn.model_dump(mode="json") for turn in turns],
            "anchor_attempts": [attempt.model_dump(mode="json") for attempt in attempts],
            "audio": [audio for item in recordings if (audio := self.copy_recording(item)) is not None],
            "report": report.model_dump(mode="json") if report else None,
            "evidence": [result.model_dump(mode="json") for result in evidence],
        }
        temporary = directory / "manifest.part"
        try:
            temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(directory / "manifest.json")
        finally:
            temporary.unlink(missing_ok=True)
