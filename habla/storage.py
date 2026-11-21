from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3

from .contracts import (
    AnchorAttempt, Catalog, Operation, PhoneticResult, Practice, Report, Status, Turn,
)
from .errors import PlatformError, not_found, state_conflict
from .identity import ActorContext


TRANSITIONS = {
    Status.READY: {Status.CONVERSATION, Status.INCOMPLETE},
    Status.CONVERSATION: {Status.ANCHORS, Status.ERROR, Status.INCOMPLETE},
    Status.ANCHORS: {Status.PROCESSING, Status.ERROR, Status.INCOMPLETE},
    Status.PROCESSING: {Status.COMPLETED, Status.ERROR, Status.INCOMPLETE},
    Status.ERROR: {Status.CONVERSATION, Status.ANCHORS, Status.PROCESSING, Status.INCOMPLETE},
}


@contextmanager
def connect(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / "habla.sqlite3")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA secure_delete = ON")
    try:
        yield db
    finally:
        db.close()


@dataclass(frozen=True)
class Draft:
    report: Report
    results: list[PhoneticResult]

    @property
    def calibration(self) -> str:
        return self.results[0].calibration_version


class PracticeStore:
    """Escritura de estados, operaciones y barrera de publicación."""

    def __init__(self, db: sqlite3.Connection, actor: ActorContext):
        self.db = db
        self.actor = actor
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS practices (
                id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES accounts(id),
                consent_id TEXT NOT NULL REFERENCES consents(id), created_at TEXT NOT NULL,
                status TEXT NOT NULL, version INTEGER NOT NULL, data TEXT NOT NULL,
                catalog TEXT NOT NULL, corpus_member TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS practice_slot ON practices ((1))
                WHERE status NOT IN ('completed', 'incomplete');
            CREATE INDEX IF NOT EXISTS practice_history ON practices(owner_id, created_at DESC, id DESC);
            CREATE TABLE IF NOT EXISTS operations (
                id TEXT PRIMARY KEY, practice_id TEXT NOT NULL REFERENCES practices(id),
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drafts (
                practice_id TEXT PRIMARY KEY REFERENCES practices(id),
                report TEXT, results TEXT NOT NULL
            );
        """)

    def create(self, practice: Practice, catalog: Catalog, corpus_member: str | None = None) -> None:
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO practices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (practice.id, self.actor.owner_id, self.actor.consent_id,
                     practice.created_at.isoformat(timespec="microseconds"), practice.status,
                     practice.state_version, practice.model_dump_json(), catalog.model_dump_json(), corpus_member),
                )
        except sqlite3.IntegrityError as error:
            if "practice_slot" not in str(error):
                raise
            raise PlatformError(
                409, "SERVER_BUSY", "El servidor está ocupado. Intenta de nuevo.", retryable=True,
            ) from error

    def _row(self, practice_id: str) -> sqlite3.Row:
        row = self.db.execute(
            "SELECT * FROM practices WHERE id = ? AND owner_id = ?",
            (practice_id, self.actor.owner_id),
        ).fetchone()
        if row is None:
            raise not_found()
        return row

    def get(self, practice_id: str) -> Practice:
        return Practice.model_validate_json(self._row(practice_id)["data"])

    def catalog(self, practice_id: str) -> Catalog:
        return Catalog.model_validate_json(self._row(practice_id)["catalog"])

    def corpus_member(self, practice_id: str) -> str | None:
        return self._row(practice_id)["corpus_member"]

    def active(self) -> list[Practice]:
        return self._practices(
            """SELECT data FROM practices WHERE owner_id = ?
               AND status NOT IN ('completed', 'incomplete')""",
            (self.actor.owner_id,),
        )

    def incomplete(self) -> list[Practice]:
        return self._practices(
            "SELECT data FROM practices WHERE owner_id = ? AND status = 'incomplete'",
            (self.actor.owner_id,),
        )

    def history(self, limit: int, after: Practice | None = None) -> list[Practice]:
        query = "SELECT data FROM practices WHERE owner_id = ?"
        args = [self.actor.owner_id]
        if after is not None:
            query += " AND (created_at, id) < (?, ?)"
            args.extend([after.created_at.isoformat(timespec="microseconds"), after.id])
        return self._practices(query + " ORDER BY created_at DESC, id DESC LIMIT ?", (*args, limit))

    def _practices(self, query: str, args: tuple) -> list[Practice]:
        return [Practice.model_validate_json(row["data"]) for row in self.db.execute(query, args)]

    def transition(
        self, current: Practice, status: Status, *, operation: Operation | None = None, **changes,
    ) -> Practice:
        if status not in TRANSITIONS.get(current.status, ()):
            raise state_conflict()
        updated = current.model_copy(update={
            "status": status, "state_version": current.state_version + 1, "reason_code": None, **changes,
        })
        with self.db:
            result = self.db.execute(
                """UPDATE practices SET status = ?, version = ?, data = ?
                   WHERE owner_id = ? AND id = ? AND version = ? AND status = ?""",
                (updated.status, updated.state_version, updated.model_dump_json(),
                 self.actor.owner_id, updated.id, current.state_version, current.status),
            )
            if result.rowcount != 1:
                raise state_conflict()
            if operation:
                self._write_operation(current.id, operation)
        return updated

    def operation(self, practice_id: str, operation: Operation) -> None:
        with self.db:
            self._write_operation(practice_id, operation)

    def _write_operation(self, practice_id: str, operation: Operation) -> None:
        self.db.execute(
            """INSERT INTO operations VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET data = excluded.data""",
            (operation.id, practice_id, operation.model_dump_json()),
        )

    def fail_open_operations(self, practice_id: str, error) -> None:
        rows = self.db.execute("SELECT data FROM operations WHERE practice_id = ?", (practice_id,))
        for row in list(rows):
            operation = Operation.model_validate_json(row["data"])
            if operation.status in {"running", "pending"}:
                self.operation(practice_id, operation.model_copy(update={"status": "failed", "error": error}))

    def save_draft(self, draft: Draft) -> None:
        with self.db:
            self.db.execute(
                """INSERT INTO drafts VALUES (?, ?, ?)
                   ON CONFLICT(practice_id) DO UPDATE SET report = excluded.report, results = excluded.results""",
                (draft.report.practice_id, draft.report.model_dump_json(),
                 self._encode_results(draft.results)),
            )

    def save_evidence(self, practice_id: str, results: list[PhoneticResult]) -> None:
        with self.db:
            self.db.execute(
                """INSERT INTO drafts VALUES (?, NULL, ?)
                   ON CONFLICT(practice_id) DO UPDATE SET results = excluded.results WHERE report IS NULL""",
                (practice_id, self._encode_results(results)),
            )

    @staticmethod
    def _encode_results(results: list[PhoneticResult]) -> str:
        return json.dumps([result.model_dump(mode="json") for result in results])

    @staticmethod
    def _decode_results(encoded: str) -> list[PhoneticResult]:
        return [PhoneticResult.model_validate(result) for result in json.loads(encoded)]

    def evidence(self, practice_id: str) -> list[PhoneticResult]:
        row = self.db.execute("SELECT results FROM drafts WHERE practice_id = ?", (practice_id,)).fetchone()
        return self._decode_results(row["results"]) if row else []

    def draft(self, practice_id: str) -> Draft | None:
        row = self.db.execute("SELECT report, results FROM drafts WHERE practice_id = ?", (practice_id,)).fetchone()
        if row is None or row["report"] is None:
            return None
        return Draft(
            Report.model_validate_json(row["report"]),
            self._decode_results(row["results"]),
        )

    def discard_draft(self, practice_id: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM drafts WHERE practice_id = ?", (practice_id,))

    def published(self, practice: Practice) -> Draft | None:
        if practice.status != Status.COMPLETED or not practice.report_id:
            return None
        draft = self.draft(practice.id)
        return draft if draft and draft.report.id == practice.report_id else None


class SimulationRecords:
    """Productores de turnos e intentos de desarrollo, separados del orquestador."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS simulated_turns (
                practice_id TEXT NOT NULL REFERENCES practices(id), id TEXT NOT NULL,
                sequence INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY (practice_id, id)
            );
            CREATE TABLE IF NOT EXISTS simulated_attempts (
                id TEXT PRIMARY KEY, practice_id TEXT NOT NULL REFERENCES practices(id),
                data TEXT NOT NULL
            );
        """)

    def write_turn(self, turn: Turn) -> None:
        with self.db:
            self.db.execute(
                """INSERT INTO simulated_turns VALUES (?, ?, ?, ?)
                   ON CONFLICT(practice_id, id) DO UPDATE SET data = excluded.data""",
                (turn.practice_id, turn.id, turn.sequence, turn.model_dump_json()),
            )

    def turns(self, practice_id: str) -> list[Turn]:
        rows = self.db.execute(
            "SELECT data FROM simulated_turns WHERE practice_id = ? ORDER BY sequence", (practice_id,),
        )
        return [Turn.model_validate_json(row["data"]) for row in rows]

    def has_turn(self, practice_id: str, turn_id: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM simulated_turns WHERE practice_id = ? AND id = ?", (practice_id, turn_id),
        ).fetchone() is not None

    def write_attempt(self, attempt: AnchorAttempt) -> None:
        with self.db:
            self.db.execute(
                """INSERT INTO simulated_attempts VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET data = excluded.data""",
                (attempt.id, attempt.practice_id, attempt.model_dump_json()),
            )

    def attempts(self, practice_id: str) -> list[AnchorAttempt]:
        rows = self.db.execute(
            "SELECT data FROM simulated_attempts WHERE practice_id = ? ORDER BY rowid", (practice_id,),
        )
        return [AnchorAttempt.model_validate_json(row["data"]) for row in rows]
