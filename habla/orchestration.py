"""Máquina de estados de SPEC-04 y coordinación de SPEC-06/09 según C-09."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
import sqlite3
import time
from uuid import UUID, uuid4

from .audio import AudioStore, Corpus, INPUT_RATE, Recording, decode_anchor
from .channel import Channel, SpeechEnd, SpeechStart, TUTOR_BYTES, student_frame, tutor_frame
from .config import Settings
from .contracts import (
    AnchorAttempt, Catalog, CreatePractice, Operation, Practice, RetryCommand, Status, Turn, utc_now,
)
from .errors import PlatformError, state_conflict
from .fixtures import CATALOG, REFERENCES
from .report_validation import validate_draft
from .simulators import Simulators, TUTOR_RATE, VALIDITY_VERSION
from .storage import PracticeStore, SimulationRecords


logger = logging.getLogger("uvicorn.error.habla")
Work = Callable[[bool, int], Awaitable[None]]


class Clock:
    wall = staticmethod(utc_now)
    monotonic = staticmethod(time.monotonic)


@dataclass
class Capture:
    turn_id: str
    start_ms: int
    recording: Recording | None = None
    last_sequence: int = -1
    frames: int = 0


@dataclass
class Generation:
    id: str
    turn: Turn
    recording: Recording
    task: asyncio.Task | None = None
    emitted_ms: int = 0


@dataclass
class Incident:
    operation: Operation
    resume: Status
    work: Work
    deadline: float


@dataclass
class Run:
    view: Practice
    catalog: Catalog
    ready_deadline: float
    channel: Channel | None = None
    deadline: float | None = None
    capture: Capture | None = None
    generation: Generation | None = None
    incident: Incident | None = None
    task: asyncio.Task | None = None
    turn_sequence: int = 0
    received_frames: int = 0
    processing_since: float | None = None


class Orchestrator:
    def __init__(
        self, settings: Settings, store: PracticeStore, audio: AudioStore, records: SimulationRecords, clock: Clock,
    ):
        self.settings = settings
        self.store = store
        self.audio = audio
        self.records = records
        self.clock = clock
        self.adapters = Simulators(settings.scenario)
        self.live: Run | None = None
        self.pending_cleanup: set[str] = set()
        self.tasks: set[asyncio.Task] = set()

    def reconcile(self) -> None:
        for view in self.store.active():
            self._abort(Run(view, self.store.catalog(view.id), 0), "SERVER_RESTARTED")
        # Una caída puede ocurrir después de revocar y antes de borrar el último archivo.
        for view in self.store.incomplete():
            if (
                self.store.evidence(view.id)
                or any(item.path.exists() for item in self.audio.for_practice(view.id))
            ):
                self.pending_cleanup.add(view.id)
        self.retry_cleanup()
        self.audio.sweep_orphans()

    async def stop(self) -> None:
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _background(self, coroutine) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def tick(self) -> None:
        run = self.live
        if run is None:
            return
        now = self.clock.monotonic()
        if run.view.status == Status.READY and now >= run.ready_deadline:
            self._abort(run, "READY_EXPIRED")
        elif run.view.status == Status.CONVERSATION and now >= run.deadline:
            self._close_conversation(run)
        elif run.incident and now >= run.incident.deadline:
            self._abort(run, "RETRY_WINDOW_EXPIRED")

    def create(self, command: CreatePractice) -> Practice:
        self.tick()
        if command.consent_id is not None and command.consent_id != self.store.actor.consent_id:
            raise PlatformError(409, "POLICY_CHANGED", "El consentimiento de desarrollo no está vigente.")
        if command.catalog_version != CATALOG.version:
            raise PlatformError(409, "CATALOG_CHANGED", "Actualiza el catálogo e intenta de nuevo.")
        view = Practice(
            id=str(uuid4()), created_at=self.clock.wall(), level=command.level, topic_id=command.topic_id,
            duration_seconds=command.duration_seconds, status=Status.READY, state_version=1,
            catalog_version=CATALOG.version, anchor_set_version=CATALOG.anchor_set_version,
        )
        self.store.create(view, CATALOG, self.settings.corpus_member)
        self.live = Run(view, CATALOG, self.clock.monotonic() + self.settings.ready_seconds)
        return view

    def _run(self, practice_id: str, version: int | None = None) -> Run:
        self.tick()
        view = self.store.get(practice_id)
        run = self.live
        if (
            run is None or run.view.id != view.id
            or (version is not None and version != view.state_version)
        ):
            raise state_conflict()
        return run

    def attach(self, practice_id: str, client_instance_id: str) -> Channel:
        run = self._run(practice_id)
        if run.view.status != Status.READY or run.channel:
            raise state_conflict()
        run.channel = Channel(practice_id, client_instance_id)
        run.channel.event("stream.ready", run.channel.ready())
        return run.channel

    def detach(self, channel: Channel) -> None:
        if self.live and self.live.channel is channel:
            self._abort(self.live, "CHANNEL_CLOSED")

    def start(self, practice_id: str, version: int) -> Practice:
        run = self._run(practice_id, version)
        if run.view.status != Status.READY or run.channel is None or run.channel.closed:
            raise state_conflict()
        now = self.clock.wall()
        run.deadline = self.clock.monotonic() + run.view.duration_seconds
        return self._move(
            run, Status.CONVERSATION, conversation_started_at=now,
            conversation_ends_at=now + timedelta(seconds=run.view.duration_seconds),
        )

    def cancel(self, practice_id: str, version: int) -> Operation:
        run = self._run(practice_id, version)
        operation = Operation(id=str(uuid4()), type="cancel", status="running", resource_id=practice_id)
        clean = self._abort(run, "CANCELLED", operation)
        return operation.model_copy(update={
            "status": "succeeded" if clean else "failed",
            "error": None if clean else self._cleanup_error().body(),
        })

    def retry(self, practice_id: str, command: RetryCommand) -> Operation:
        run = self._run(practice_id, command.state_version)
        incident = run.incident
        if run.view.status != Status.ERROR or incident is None or incident.operation.id != command.operation_id:
            raise state_conflict()
        run.incident = None
        operation = incident.operation.model_copy(update={"status": "running", "error": None})
        if incident.resume == Status.CONVERSATION and self.clock.monotonic() >= run.deadline:
            self._move(run, Status.ANCHORS, operation=operation.model_copy(update={"status": "succeeded"}))
        else:
            self._move(run, incident.resume, operation=operation)
            self._launch(run, incident.work, operation)
        return operation

    def _move(self, run: Run, status: Status, **changes) -> Practice:
        run.view = self.store.transition(run.view, status, **changes)
        self._notify(run, "practice.state_changed", {
            "status": status.value, "state_version": run.view.state_version, "reason_code": run.view.reason_code,
            "conversation_ends_at": run.view.model_dump(mode="json")["conversation_ends_at"],
        })
        logger.info("practice_transition id=%s state=%s version=%d", run.view.id, status, run.view.state_version)
        return run.view

    @staticmethod
    def _notify(run: Run, kind: str, payload: dict) -> None:
        if run.channel:
            run.channel.event(kind, payload)

    @staticmethod
    def _cancel_job(run: Run) -> None:
        if run.task and run.task is not asyncio.current_task():
            run.task.cancel()
        run.task = None

    def _close_conversation(self, run: Run) -> None:
        self._cancel_job(run)
        self._stop_tutor(run)
        run.capture = None
        self.store.fail_open_operations(
            run.view.id,
            PlatformError(409, "CONVERSATION_ENDED", "Terminó el tiempo de conversación.").body(),
        )
        self._move(run, Status.ANCHORS)

    def _abort(self, run: Run, code: str, operation: Operation | None = None) -> bool:
        self._cancel_job(run)
        run.capture = None
        self._move(run, Status.INCOMPLETE, reason_code=code, operation=operation)
        self._stop_tutor(run)
        self.store.fail_open_operations(
            run.view.id, PlatformError(409, code, "La práctica quedó incompleta.").body(),
        )
        if self.live is run:
            self.live = None
        clean = self._cleanup_incomplete(run.view)
        if operation:
            self.store.operation(run.view.id, operation.model_copy(update={
                "status": "succeeded" if clean else "failed",
                "error": None if clean else self._cleanup_error().body(),
            }))
        if run.channel:
            run.channel.finish()
        return clean

    @staticmethod
    def _cleanup_error() -> PlatformError:
        return PlatformError(503, "CLEANUP_FAILED", "La limpieza del audio quedó pendiente.", retryable=True)

    def _corpus(self, practice_id: str) -> Corpus | None:
        member = self.store.corpus_member(practice_id)
        return Corpus(self.settings.data_dir, member) if member else None

    def _archive(self, practice: Practice) -> None:
        if corpus := self._corpus(practice.id):
            draft = self.store.draft(practice.id)
            corpus.archive(
                practice, self.records.turns(practice.id), self.records.attempts(practice.id),
                self.audio.for_practice(practice.id), draft.report if draft else None,
                draft.results if draft else self.store.evidence(practice.id),
            )

    def _cleanup_incomplete(self, practice: Practice) -> bool:
        try:
            self._archive(practice)
            self.audio.clean(practice.id, set())
            self.store.discard_draft(practice.id)
        except (OSError, sqlite3.Error) as error:
            self.pending_cleanup.add(practice.id)
            logger.warning("audio_cleanup_pending id=%s cause=%s", practice.id, type(error).__name__)
            return False
        self.pending_cleanup.discard(practice.id)
        return True

    def retry_cleanup(self) -> None:
        for practice_id in list(self.pending_cleanup):
            self._cleanup_incomplete(self.store.get(practice_id))

    def _is_current(self, run: Run, version: int) -> bool:
        return self.live is run and run.view.state_version == version

    def _launch(self, run: Run, work: Work, retrying: Operation | None = None) -> None:
        version = run.view.state_version
        resume = run.view.status

        async def invoke() -> None:
            try:
                async with asyncio.timeout(self.settings.model_seconds):
                    await work(retrying is not None, version)
                if retrying and run.view.status != Status.INCOMPLETE:
                    self.store.operation(run.view.id, retrying.model_copy(update={"status": "succeeded"}))
            except TimeoutError:
                self._job_failed(run, version, resume, work, retrying, PlatformError(
                    504, "DEADLINE_EXCEEDED", "La operación excedió el tiempo permitido.", retryable=True,
                ))
            except PlatformError as error:
                self._job_failed(run, version, resume, work, retrying, error)
            except (OSError, sqlite3.Error) as error:
                logger.warning("practice_work_failed id=%s cause=%s", run.view.id, type(error).__name__)
                self._job_failed(run, version, resume, work, retrying, self._cleanup_error())
            finally:
                if run.task is asyncio.current_task():
                    run.task = None

        run.task = self._background(invoke())

    def _job_failed(
        self, run: Run, version: int, resume: Status, work: Work,
        retrying: Operation | None, error: PlatformError,
    ) -> None:
        if not self._is_current(run, version):
            return
        operation = Operation(
            id=retrying.id if retrying else str(uuid4()), type=retrying.type if retrying else resume.value,
            status="failed", resource_id=run.view.id, error=error.body(),
        )
        can_retry = error.retryable and retrying is None
        if can_retry:
            run.capture = None
            self._stop_tutor(run)
            run.incident = Incident(operation, resume, work, self.clock.monotonic() + self.settings.retry_seconds)
            self._move(run, Status.ERROR, reason_code=error.code, operation=operation)
        else:
            self.store.operation(run.view.id, operation)
        self._notify(run, "practice.error", {
            "operation_id": operation.id, "code": error.code, "retryable": can_retry,
            "resume_state": resume.value if can_retry else None,
        })
        if not can_retry:
            self._abort(run, "RETRY_EXHAUSTED" if retrying else error.code)

    def _conversation(self, channel: Channel) -> Run | None:
        self.tick()
        run = self.live
        if run and run.channel is channel and run.view.status == Status.CONVERSATION:
            return run
        return None

    def speech_start(self, channel: Channel, command: SpeechStart) -> None:
        run = self._conversation(channel)
        if run is None or run.capture is not None or (run.task and not run.task.done()):
            return
        try:
            turn_id = str(UUID(command.turn_id))
        except ValueError:
            return
        if turn_id != command.turn_id:
            return
        if self.records.has_turn(run.view.id, command.turn_id):
            return
        if run.generation:
            same_generation = command.interrupted_generation_id == run.generation.id
            self._stop_tutor(run, (command.heard_until_ms or 0) if same_generation else 0)
        run.capture = Capture(command.turn_id, self._elapsed(run))

    def receive_audio(self, channel: Channel, data: bytes) -> None:
        run = self._conversation(channel)
        if run is None or run.capture is None or run.received_frames >= run.view.duration_seconds * 50:
            return
        capture = run.capture
        frame = student_frame(data, channel.id, capture.turn_id)
        if frame is None or frame[0] <= capture.last_sequence:
            return
        sequence, pcm = frame
        if sequence > capture.last_sequence + 1:
            logger.info("student_frame_gap id=%s missing=%d", run.view.id, sequence - capture.last_sequence - 1)
        if capture.recording is None:
            capture.recording = self.audio.create(run.view.id, "conversation_temp", INPUT_RATE)
        self.audio.append(capture.recording, pcm)
        capture.last_sequence = sequence
        capture.frames += 1
        run.received_frames += 1

    def speech_end(self, channel: Channel, command: SpeechEnd) -> None:
        run = self._conversation(channel)
        if run is None or run.capture is None or run.capture.turn_id != command.turn_id:
            return
        capture = run.capture
        run.capture = None
        if capture.recording is None or command.last_chunk_seq != capture.last_sequence:
            return
        self.audio.mark_available(capture.recording, capture.frames * 20)
        start = self.clock.monotonic()
        end_ms = min(run.view.duration_seconds * 1000, max(
            self._elapsed(run), capture.start_ms + capture.frames * 20,
        ))
        student_text = None
        tutor_text = None

        async def answer(retry: bool, version: int) -> None:
            nonlocal student_text, tutor_text
            if student_text is None:
                text = await self.adapters.asr(capture.recording.path.read_bytes(), retry)
                self.tick()
                if not self._is_current(run, version):
                    return
                if text:
                    self._turn(run, capture.turn_id, "student", text, "final", capture.recording,
                               capture.start_ms, end_ms)
                student_text = text
            if tutor_text is None:
                tutor_text = await self.adapters.tutor(run.view, run.catalog, retry)
            response = await self.adapters.tts(tutor_text, retry)
            self.tick()
            if not self._is_current(run, version):
                return
            self._speak(run, tutor_text, response, start)

        self._launch(run, answer)

    def _elapsed(self, run: Run) -> int:
        return min(run.view.duration_seconds * 1000, max(0, int(
            (self.clock.monotonic() - (run.deadline - run.view.duration_seconds)) * 1000,
        )))

    def _turn(
        self, run: Run, turn_id: str, speaker: str, text: str, status: str,
        recording: Recording, start_ms: int, end_ms: int,
    ) -> Turn:
        run.turn_sequence += 1
        turn = Turn(
            id=turn_id, practice_id=run.view.id, sequence=run.turn_sequence, speaker=speaker, text=text,
            status=status, audio_id=recording.asset.id, start_ms=start_ms, end_ms=end_ms,
        )
        self.records.write_turn(turn)
        self._notify(run, "transcript.updated", turn.model_dump(mode="json"))
        return turn

    def _speak(self, run: Run, text: str, pcm: bytes, student_ended_at: float) -> None:
        recording = self.audio.create(run.view.id, "conversation_temp", TUTOR_RATE)
        elapsed = self._elapsed(run)
        turn = self._turn(run, str(uuid4()), "tutor", text, "partial", recording, elapsed, elapsed)
        generation = Generation(str(uuid4()), turn, recording)
        run.generation = generation
        ids = {"turn_id": turn.id, "generation_id": generation.id}
        self._notify(run, "tutor.audio_started", ids)

        async def play() -> None:
            try:
                for sequence, offset in enumerate(range(0, len(pcm), TUTOR_BYTES)):
                    self.tick()
                    if run.generation is not generation:
                        return
                    chunk = pcm[offset:offset + TUTOR_BYTES].ljust(TUTOR_BYTES, b"\0")
                    self.audio.append(recording, chunk)
                    run.channel.send(tutor_frame(run.channel.id, turn.id, generation.id, sequence, chunk))
                    generation.emitted_ms += 20
                    if sequence == 0:
                        logger.info("latency metric=tutor_first_frame_queued simulation=true ms=%.1f",
                                    (self.clock.monotonic() - student_ended_at) * 1000)
                    await asyncio.sleep(0.02)
                self._finish_tutor(run, generation, None)
                self._notify(run, "tutor.audio_ended", ids)
            except (OSError, sqlite3.Error):
                if self.live is run:
                    self._abort(run, "AUDIO_STORAGE_FAILED")

        generation.task = self._background(play())

    def _finish_tutor(self, run: Run, generation: Generation, heard: int | None) -> None:
        run.generation = None
        turn = generation.turn.model_copy(update={
            "status": "final" if heard is None else "interrupted", "end_ms": self._elapsed(run),
            "heard_until_ms": heard,
        })
        self.audio.mark_available(generation.recording, generation.emitted_ms)
        self.records.write_turn(turn)
        self._notify(run, "transcript.updated", turn.model_dump(mode="json"))

    def _stop_tutor(self, run: Run, heard_ms: int = 0) -> None:
        generation = run.generation
        if generation is None:
            return
        started = self.clock.monotonic()
        if generation.task is not asyncio.current_task():
            generation.task.cancel()
        heard = min(heard_ms, generation.emitted_ms)
        try:
            self._finish_tutor(run, generation, heard)
        except (OSError, sqlite3.Error) as error:
            logger.warning("tutor_recording_failed id=%s cause=%s", run.view.id, type(error).__name__)
        self._notify(run, "tutor.interrupted", {
            "turn_id": generation.turn.id, "generation_id": generation.id, "heard_until_ms": heard,
        })
        logger.info("latency metric=interrupt_server simulation=true ms=%.1f",
                    (self.clock.monotonic() - started) * 1000)

    def check_anchor_phase(self, practice_id: str) -> None:
        if self._run(practice_id).view.status != Status.ANCHORS:
            raise state_conflict()

    def submit_anchor(
        self, practice_id: str, version: int, phrase_id: str, data: bytes, media_type: str,
    ) -> AnchorAttempt:
        run = self._run(practice_id, version)
        if run.view.status != Status.ANCHORS:
            raise state_conflict()
        attempts = self.records.attempts(practice_id)
        if any(item.status == "pending" for item in attempts):
            raise PlatformError(409, "ATTEMPT_PENDING", "Espera el resultado del intento pendiente.")
        expected = run.catalog.anchors[sum(item.status == "valid" for item in attempts)]
        if phrase_id != expected.id:
            raise PlatformError(409, "PHRASE_CLOSED", "La frase no corresponde al turno actual.")
        number = 1 + sum(item.phrase_id == phrase_id for item in attempts)
        if number > 3:
            raise PlatformError(409, "ATTEMPTS_EXHAUSTED", "Se agotaron los intentos de esta frase.")
        data, duration = decode_anchor(data, media_type, self.settings.max_anchor_seconds)
        recording = self.audio.create(practice_id, "anchor", INPUT_RATE, data, duration)
        attempt = AnchorAttempt(
            id=str(uuid4()), practice_id=practice_id, phrase_id=phrase_id, attempt_number=number,
            audio_id=recording.asset.id, status="pending", validity_version=VALIDITY_VERSION,
        )
        self.records.write_attempt(attempt)

        async def validate(retry: bool, expected_version: int) -> None:
            reason = await self.adapters.validate_anchor(data, retry)
            if not self._is_current(run, expected_version):
                return
            if reason:
                if corpus := self._corpus(practice_id):
                    corpus.copy_recording(recording)
                self.audio.discard(recording)
            else:
                self.audio.mark_available(recording, duration)
            status = "invalid" if reason else "valid"
            result = attempt.model_copy(update={"status": status, "invalid_reason": reason})
            self.records.write_attempt(result)
            self._notify(run, "anchor.validated", {
                "attempt_id": result.id, "phrase_id": phrase_id, "status": status,
                "invalid_reason": reason, "attempts_remaining": 3 - number if reason else 0,
            })
            if reason and number == 3:
                self._abort(run, "ATTEMPTS_EXHAUSTED")
            elif not reason and expected.position == 5:
                self._move(run, Status.PROCESSING)
                run.processing_since = self.clock.monotonic()
                self._launch(run, lambda retry, version: self._process(run, retry, version))

        self._launch(run, validate)
        return attempt

    async def _process(self, run: Run, retry: bool, version: int) -> None:
        practice = run.view
        attempts = [item for item in self.records.attempts(practice.id) if item.status == "valid"]
        retained = {item.audio_id: self.audio.get(item.audio_id) for item in attempts}
        if len(retained) != 5 or any(
            item.asset.status != "available" or not item.path.is_file() for item in retained.values()
        ):
            raise PlatformError(503, "INPUT_UNAVAILABLE", "No están disponibles las cinco muestras válidas.")
        draft = self.store.draft(practice.id)
        if draft is None:
            self._notify(run, "processing.updated", {"stage": "acoustic"})
            results = []
            collecting = self.store.corpus_member(practice.id) is not None
            for phrase, attempt in zip(run.catalog.anchors, attempts, strict=True):
                result = await self.adapters.evaluate(practice, phrase, retained[attempt.audio_id])
                if not self._is_current(run, version):
                    return
                results.append(result)
                if collecting:
                    self.store.save_evidence(practice.id, results)
            self._notify(run, "processing.updated", {"stage": "linguistic"})
            turns = self.records.turns(practice.id)
            vocabulary = await self.adapters.linguistic(turns)
            self._notify(run, "processing.updated", {"stage": "report"})
            payload = await self.adapters.build_report(practice, run.catalog, results, vocabulary, retry)
            if not self._is_current(run, version):
                return
            draft = validate_draft(
                payload, results, practice, run.catalog, attempts,
                {key: value.asset.duration_ms for key, value in retained.items()}, turns, set(REFERENCES),
            )
            self.store.save_draft(draft)
        self._notify(run, "processing.updated", {"stage": "cleanup"})
        self._archive(practice)
        self.audio.clean(practice.id, set(retained))
        self.adapters.fault("commit", retry)
        if not self._is_current(run, version):
            return
        self._move(run, Status.COMPLETED, report_id=draft.report.id, evaluator_version=draft.report.evaluator_version)
        self._notify(run, "report.ready", {"report_id": draft.report.id, "state_version": run.view.state_version})
        logger.info("latency metric=report_ready simulation=true ms=%.1f",
                    (self.clock.monotonic() - run.processing_since) * 1000)
        self.live = None
        if run.channel:
            run.channel.finish()
