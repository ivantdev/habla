from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import logging
import time
from uuid import UUID, uuid4
import wave

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from starlette.websockets import WebSocketDisconnect

from habla.app import API, create_app
from habla.audio import AudioStore, INPUT_RATE, wav_bytes
from habla.channel import AUDIO_PROFILE, HEADER, MAX_FRAME_BYTES, ZERO_UUID
from habla.config import Settings
from habla.contracts import AudioAsset, ConsentRecord, Practice, Status, utc_now
from habla.fixtures import CATALOG, FIXTURE_PATH, REFERENCES, fixture_text, tone
from habla.identity import BASE_CONSENT_ID, seed_base_user
from habla.orchestration import Clock
from habla.schema import SCHEMA_PATH, schema_text
from habla.simulators import Simulators
from habla.storage import PracticeStore, connect


ORIGIN = "http://127.0.0.1:3000"
SAMPLE = wav_bytes(tone(INPUT_RATE, 420, 320), INPUT_RATE)


class TestClock(Clock):
    __test__ = False

    def __init__(self):
        self.value = 0.0
        self.epoch = datetime(2026, 10, 30, tzinfo=timezone.utc)

    def wall(self):
        return self.epoch + timedelta(seconds=self.value)

    def monotonic(self):
        return self.value


@contextmanager
def client(settings, clock=None):
    with TestClient(create_app(settings, clock), base_url=ORIGIN + API, headers={"Origin": ORIGIN}) as session:
        yield session


def select(duration=300):
    return {"level": "A2", "topic_id": "restaurant", "duration_seconds": duration, "catalog_version": CATALOG.version}


def create(session, duration=300):
    response = session.post("practices", json=select(duration))
    assert response.status_code == 201, response.text
    return response.json()


def practice(session, practice_id):
    response = session.get(f"practices/{practice_id}")
    assert response.status_code == 200, response.text
    return response.json()


def wait_for(session, practice_id, status):
    deadline = time.monotonic() + 4
    while True:
        view = practice(session, practice_id)
        if view["status"] == status:
            return view
        assert time.monotonic() < deadline, view
        time.sleep(0.015)


class TestStream:
    __test__ = False

    def __init__(self, socket, practice_id):
        self.socket = socket
        self.practice_id = practice_id
        self.stream_id = None
        self.seq = 0

    def send(self, event, payload):
        self.seq += 1
        self.socket.send_json({
            "v": 1, "event_id": str(uuid4()), "practice_id": self.practice_id, "stream_id": self.stream_id,
            "seq": self.seq, "occurred_at": utc_now().isoformat(), "type": event, "payload": payload,
        })

    def get(self, kind):
        while True:
            received = self.socket.receive()
            assert received["type"] == "websocket.send", received
            if "text" in received:
                event = json.loads(received["text"])
                if event["type"] == kind:
                    return event

    def open(self, profile=AUDIO_PROFILE):
        self.send("stream.open", {"audio_profile_id": profile, "client_instance_id": str(uuid4())})

    def turn(self, *, end=True, acknowledge=None):
        turn = uuid4()
        self.send("student.speech_started", {
            "turn_id": str(turn), "client_offset_ms": 0, "interrupted_generation_id": acknowledge, "heard_until_ms": 20,
        })
        pcm = SAMPLE[44:44 + 640]
        for sequence in (0, 0, 2, 1):  # duplicados, hueco y paquete fuera de orden
            self.socket.send_bytes(
                HEADER.pack(1, 1, 0, sequence, UUID(self.stream_id).bytes, turn.bytes, ZERO_UUID) + pcm,
            )
        if end:
            self.send("student.turn_ended", {"turn_id": str(turn), "last_chunk_seq": 2})
        return str(turn)


@contextmanager
def started(session, duration=300):
    view = create(session, duration)
    path = f"practices/{view['id']}"
    with session.websocket_connect(f"ws://127.0.0.1:3000{API}/{path}/stream") as socket:
        stream = TestStream(socket, view["id"])
        stream.open()
        ready = stream.get("stream.ready")
        stream.stream_id = ready["stream_id"]
        assert ready["payload"]["max_frame_bytes"] == MAX_FRAME_BYTES == 938
        response = session.post(f"{path}/start", json={"state_version": 1})
        assert response.status_code == 200, response.text
        assert stream.get("practice.state_changed")["payload"]["status"] == "conversation"
        yield response.json(), stream


def upload(session, view, index=0, *, data=SAMPLE, media_type="audio/wav"):
    return session.post(
        f"practices/{view['id']}/anchor-attempts",
        data={"state_version": str(view["state_version"]), "phrase_id": CATALOG.anchors[index].id},
        files={"audio": ("muestra.wav", data, media_type)},
    )


def anchors(session, clock, view):
    clock.value += view["duration_seconds"]
    return wait_for(session, view["id"], "anchors")


def submit_five(session, view, stream):
    ids = []
    for index in range(5):
        response = upload(session, view, index)
        assert response.status_code == 202, response.text
        item = response.json()
        assert item["status"] == "pending"
        ids.append(item["audio_id"])
        validated = stream.get("anchor.validated")
        assert validated["payload"]["status"] == "valid"
        assert session.get(f"audio/{item['audio_id']}").status_code == 404 or index == 4
        if index < 4:
            assert practice(session, view["id"])["status"] == "anchors"
            assert session.get(f"practices/{view['id']}/report").status_code == 409
    return ids


def test_schema_and_fixtures_match_and_reject_unknown_state():
    assert SCHEMA_PATH.read_text(encoding="utf-8") == schema_text()
    assert FIXTURE_PATH.read_text(encoding="utf-8") == fixture_text()
    examples = json.loads(fixture_text())
    ConsentRecord.model_validate_json(json.dumps(examples["consent"]))
    for raw in examples["audio_assets"]:
        AudioAsset.model_validate_json(json.dumps(raw))
    for raw in examples["practices"]:
        Practice.model_validate_json(json.dumps(raw))
    with pytest.raises(ValidationError):
        Practice.model_validate_json(json.dumps({**raw, "status": "unknown"}))


def test_configuration_and_origin_before_recording(tmp_path, monkeypatch):
    monkeypatch.setenv("HABLA_CORPUS_ENABLED", "1")
    monkeypatch.delenv("HABLA_CORPUS_MEMBER", raising=False)
    with pytest.raises(RuntimeError, match="HABLA_CORPUS_MEMBER"):
        with TestClient(create_app()):
            pass
    with client(Settings(tmp_path)) as session:
        assert session.get("health").json()["simulation"] is True
        assert session.get("dev/fixtures").json() == session.get("dev/fixtures").json()
        assert session.get("catalog", headers={"Origin": "http://other.invalid"}).status_code == 403
        assert session.post("practices", json={**select(), "owner_id": "otro"}).status_code == 422
        assert session.post("practices", json={**select(), "consent_id": "otro"}).status_code == 409
        view = create(session)
        path = f"ws://127.0.0.1:3000{API}/practices/{view['id']}/stream"
        with pytest.raises(WebSocketDisconnect):
            with session.websocket_connect(path, headers={"Origin": "http://other.invalid"}):
                pass
        with session.websocket_connect(path) as socket:
            stream = TestStream(socket, view["id"])
            stream.open("incompatible")
            assert stream.get("stream.rejected")["payload"]["code"] == "UNSUPPORTED_AUDIO_PROFILE"
        assert session.post(f"practices/{view['id']}/start", json={"state_version": 1}).status_code == 409
        assert list((tmp_path / "audio").iterdir()) == []


def test_atomic_slot_and_history_under_load(tmp_path):
    with client(Settings(tmp_path)) as session:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: session.post("practices", json=select()), range(2)))
        assert sorted(response.status_code for response in responses) == [201, 409]
        view = next(response.json() for response in responses if response.status_code == 201)
        with session.websocket_connect(f"ws://127.0.0.1:3000{API}/practices/{view['id']}/stream") as socket:
            stream = TestStream(socket, view["id"])
            stream.open()
            stream.get("stream.ready")
            busy = session.post("practices", json=select())
            assert busy.json()["error"]["code"] == "SERVER_BUSY"
            assert session.get("history").json()["items"][0]["id"] == view["id"]
        assert wait_for(session, view["id"], "incomplete")["reason_code"] == "CHANNEL_CLOSED"
        create(session)


@pytest.mark.parametrize("duration", [300, 600])
def test_clock_and_stale_commands(tmp_path, duration):
    clock = TestClock()
    with client(Settings(tmp_path), clock) as session, started(session, duration) as (view, stream):
        assert view["conversation_ends_at"] == (clock.epoch + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z")
        stale = session.post(f"practices/{view['id']}/start", json={"state_version": 1})
        assert stale.json()["error"]["code"] == "STATE_CONFLICT"
        clock.value = duration - 0.001
        assert practice(session, view["id"])["status"] == "conversation"
        clock.value = duration
        assert practice(session, view["id"])["status"] == "anchors"
        assert stream.get("practice.state_changed")["payload"]["status"] == "anchors"
        stream.turn()
        assert not list((tmp_path / "audio").iterdir())


def test_report_audio_history_and_comparison(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="uvicorn.error.habla")
    clock = TestClock()
    completed = []
    with client(Settings(tmp_path), clock) as session:
        for _ in range(2):
            with started(session) as (view, stream):
                stream.turn()
                assert stream.get("transcript.updated")["payload"]["speaker"] == "student"
                stream.get("tutor.audio_ended")
                view = anchors(session, clock, view)
                bad = upload(session, view, media_type="audio/ogg")
                assert bad.status_code == 415
                ids = submit_five(session, view, stream)
                event = stream.get("report.ready")
                check = wait_for(session, view["id"], "completed")
                assert event["payload"]["report_id"] == check["report_id"]
                assert list((tmp_path / "audio").glob("*.bin"))
                report = session.get(f"practices/{view['id']}/report")
                assert report.status_code == 200
                assert report.headers["cache-control"] == "no-store"
                assert report.json()["id"] == check["report_id"]
                assert report.json()["categories"]["vocabulary"]["observations"][0]["student_quote"] == "I like this place."
                partial = session.get(f"audio/{ids[0]}", headers={"Range": "bytes=0-43"})
                assert partial.status_code == 206
                assert partial.content[:4] == b"RIFF" and len(partial.content) == 44
                assert partial.headers["cache-control"] == "no-store"
                assert session.get(f"references/{ids[0]}").status_code == 404
                reference = session.get(f"references/{next(iter(REFERENCES))}")
                with wave.open(BytesIO(reference.content), "rb") as wav:
                    assert wav.getframerate() == INPUT_RATE
                completed.append(view["id"])
        assert len(list((tmp_path / "audio").iterdir())) == 10
        page = session.get("history", params={"limit": 1}).json()
        assert [item["id"] for item in page["items"]] == [completed[1]]
        page = session.get("history", params={"limit": 1, "cursor": page["next_cursor"]}).json()
        assert [item["id"] for item in page["items"]] == [completed[0]]
        assert page["next_cursor"] is None
        comparison = session.get("comparisons", params=dict(zip(("left", "right"), completed))).json()
        assert comparison["compatible"]
        theta = next(row for row in comparison["sounds"] if row["sound"] == "θ")
        assert theta["left"] == {"evaluated_opportunities": 1, "detected_errors": 1, "not_evaluated_opportunities": 1}
        assert session.get("comparisons", params={"left": completed[0], "right": "otro"}).status_code == 404
        assert session.get("comparisons", params={"left": completed[0], "right": completed[0]}).status_code == 409
        incomplete = create(session)
        assert session.post(f"practices/{incomplete['id']}/cancel", json={"state_version": 1}).status_code == 202
        assert session.get("comparisons", params={"left": completed[0], "right": incomplete["id"]}).status_code == 409
    with connect(tmp_path) as db, db:
        row = db.execute("SELECT results FROM drafts WHERE practice_id = ?", (completed[1],)).fetchone()
        changed = json.loads(row["results"])
        for result in changed:
            result["calibration_version"] = "distinta"
        db.execute("UPDATE drafts SET results = ? WHERE practice_id = ?", (json.dumps(changed), completed[1]))
    with client(Settings(tmp_path), clock) as session:
        response = session.get("comparisons", params=dict(zip(("left", "right"), completed)))
        assert response.status_code == 409 and response.json()["error"]["code"] == "INCOMPATIBLE_SESSIONS"
    assert "metric=tutor_first_frame_queued" in caplog.text and "metric=report_ready" in caplog.text


def test_interruption_records_only_ordered_frames(tmp_path):
    with client(Settings(tmp_path), TestClock()) as session, started(session) as (view, stream):
        stream.turn()
        generation = stream.get("tutor.audio_started")["payload"]["generation_id"]
        stream.turn(acknowledge=generation)
        event = stream.get("tutor.interrupted")
        assert event["payload"]["generation_id"] == generation
        stream.get("tutor.audio_started")
        raw = [asset.read_bytes() for asset in (tmp_path / "audio").glob("*.bin")]
        assert sum(len(data) == 2 * 640 for data in raw) == 2
        operation = session.post(f"practices/{view['id']}/cancel", json={"state_version": view["state_version"]})
        assert operation.status_code == 202
        assert operation.json()["status"] == "succeeded"
        assert wait_for(session, view["id"], "incomplete")["reason_code"] == "CANCELLED"
        assert not list((tmp_path / "audio").iterdir())


@pytest.mark.parametrize("stage", ["asr", "tutor", "tts"])
def test_voice_failure_manual_retry_keeps_deadline(tmp_path, stage):
    config = Settings(tmp_path, mode="demo", scenario=f"{stage}_fail_once")
    with client(config, TestClock()) as session, started(session) as (view, stream):
        stream.turn()
        error = stream.get("practice.error")["payload"]
        assert error["code"] == f"{stage.upper()}_UNAVAILABLE" and error["retryable"]
        failed = wait_for(session, view["id"], "recoverable_error")
        command = {"state_version": failed["state_version"], "operation_id": error["operation_id"]}
        response = session.post(f"practices/{view['id']}/retry", json=command)
        assert response.status_code == 202
        assert response.json()["id"] == error["operation_id"]
        assert session.post(f"practices/{view['id']}/retry", json=command).json()["error"]["code"] == "STATE_CONFLICT"
        stream.get("tutor.audio_ended")
        resumed = wait_for(session, view["id"], "conversation")
        assert resumed["conversation_ends_at"] == view["conversation_ends_at"]


def test_anchor_failure_keeps_original_attempt(tmp_path):
    clock = TestClock()
    config = Settings(tmp_path, mode="demo", scenario="anchor_fail_once")
    with client(config, clock) as session, started(session) as (view, stream):
        view = anchors(session, clock, view)
        original = upload(session, view).json()
        error = stream.get("practice.error")["payload"]
        failed = wait_for(session, view["id"], "recoverable_error")
        assert session.post(f"practices/{view['id']}/retry", json={
            "state_version": failed["state_version"], "operation_id": error["operation_id"],
        }).status_code == 202
        assert stream.get("anchor.validated")["payload"]["attempt_id"] == original["id"]
        attempts = session.get(f"practices/{view['id']}/anchor-attempts").json()["items"]
        assert len(attempts) == 1 and attempts[0]["status"] == "valid"


@pytest.mark.parametrize("scenario,outcome", [
    ("commit_fail_once", "completed"),
    ("report_unavailable", "incomplete"),
    ("file_cleanup_failed", "completed"),
])
def test_report_retry_and_retention(tmp_path, scenario, outcome, monkeypatch):
    clock = TestClock()
    config = Settings(
        tmp_path, mode="demo", scenario=scenario,
        corpus_member="fixture-A" if scenario == "report_unavailable" else None,
    )
    if scenario == "file_cleanup_failed":
        config = Settings(tmp_path)
        original = AudioStore.clean
        failed_once = False

        def locked_file(self, practice_id, retain):
            nonlocal failed_once
            if retain and not failed_once:
                failed_once = True
                raise PermissionError("fixture")
            original(self, practice_id, retain)

        monkeypatch.setattr(AudioStore, "clean", locked_file)
    with client(config, clock) as session, started(session) as (view, stream):
        stream.turn()
        stream.get("tutor.audio_ended")
        view = anchors(session, clock, view)
        submit_five(session, view, stream)
        error = stream.get("practice.error")["payload"]
        failed = wait_for(session, view["id"], "recoverable_error")
        path = f"practices/{view['id']}"
        assert session.get(f"{path}/report").status_code == 409
        if scenario == "commit_fail_once":
            assert len(list((tmp_path / "audio").iterdir())) == 5
        assert session.post(f"{path}/retry", json={
            "state_version": failed["state_version"], "operation_id": error["operation_id"],
        }).status_code == 202
        result = wait_for(session, view["id"], outcome)
        if outcome == "completed":
            assert stream.get("report.ready")["payload"]["report_id"] == result["report_id"]
            assert len(list((tmp_path / "audio").iterdir())) == 5
        else:
            assert result["reason_code"] == "RETRY_EXHAUSTED"
            assert session.get(f"{path}/report").status_code == 409
            assert not list((tmp_path / "audio").iterdir())
            archive = tmp_path / "corpus" / view["id"] / "manifest.json"
            manifest = json.loads(archive.read_text(encoding="utf-8"))
            assert len(manifest["evidence"]) == 5 and manifest["report"] is None


def test_cancel_during_slow_evaluation_prevents_late_publish(tmp_path):
    clock = TestClock()
    config = Settings(tmp_path, mode="demo", scenario="slow_evaluation")
    with client(config, clock) as session, started(session) as (view, stream):
        view = anchors(session, clock, view)
        submit_five(session, view, stream)
        processing = wait_for(session, view["id"], "processing")
        assert session.get("history").status_code == 200
        assert session.post(
            f"practices/{view['id']}/cancel", json={"state_version": processing["state_version"]},
        ).status_code == 202
        assert wait_for(session, view["id"], "incomplete")["report_id"] is None
        assert session.get(f"practices/{view['id']}/report").status_code == 409
        assert not list((tmp_path / "audio").iterdir())


def test_invalid_anchor_limit_and_internal_corpus(tmp_path):
    clock = TestClock()
    config = Settings(tmp_path, mode="demo", scenario="anchor_invalid", corpus_member="fixture-A")
    with client(config, clock) as session, started(session) as (view, stream):
        stream.turn(end=False)
        view = anchors(session, clock, view)
        for number in range(1, 4):
            response = upload(session, view)
            assert response.status_code == 202
            assert response.json()["attempt_number"] == number
            assert stream.get("anchor.validated")["payload"]["attempts_remaining"] == 3 - number
        result = wait_for(session, view["id"], "incomplete")
        assert result["reason_code"] == "ATTEMPTS_EXHAUSTED"
        assert upload(session, view).status_code == 409
        assert not list((tmp_path / "audio").iterdir())
        archive = tmp_path / "corpus" / view["id"]
        manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["member"] == "fixture-A" and manifest["simulation"] is True
        assert len(list((archive / "audio").glob("*.wav"))) == 3
        assert len(list((archive / "audio").glob("*.pcm"))) == 1
        assert session.get(f"corpus/{view['id']}/manifest.json").status_code == 404


def test_corpus_copies_report_evidence_and_conversation_before_cleanup(tmp_path):
    clock = TestClock()
    with client(Settings(tmp_path, corpus_member="fixture-A"), clock) as session, started(session) as (view, stream):
        stream.turn()
        stream.get("tutor.audio_ended")
        view = anchors(session, clock, view)
        submit_five(session, view, stream)
        result = wait_for(session, view["id"], "completed")
        manifest_file = tmp_path / "corpus" / view["id"] / "manifest.json"
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest["report"]["id"] == result["report_id"]
        assert len(manifest["evidence"]) == 5
        assert any(turn["speaker"] == "student" for turn in manifest["transcript"])
        assert any(item["source"] == "conversation_temp" for item in manifest["audio"])
        assert all((manifest_file.parent / item["file"]).is_file() for item in manifest["audio"])
        assert len(list((tmp_path / "audio").iterdir())) == 5


def test_expired_retry_window_releases_slot(tmp_path):
    config = Settings(tmp_path, mode="demo", scenario="asr_fail_once")
    clock = TestClock()
    with client(config, clock) as session, started(session) as (view, stream):
        stream.turn()
        error = stream.get("practice.error")["payload"]
        failed = wait_for(session, view["id"], "recoverable_error")
        clock.value += config.retry_seconds
        response = session.post(f"practices/{view['id']}/retry", json={
            "state_version": failed["state_version"], "operation_id": error["operation_id"],
        })
        assert response.status_code == 409
        assert practice(session, view["id"])["reason_code"] == "RETRY_WINDOW_EXPIRED"
        assert not list((tmp_path / "audio").iterdir())
        create(session)


def test_restart_reconciles_unfinished_practice_and_orphan_bytes(tmp_path):
    with connect(tmp_path) as db:
        actor = seed_base_user(db)
        assert actor.consent_id == BASE_CONSENT_ID
        store = PracticeStore(db, actor)
        view = Practice(
            id=str(uuid4()), created_at=utc_now(), level="A2", topic_id="restaurant", duration_seconds=300,
            status=Status.READY, state_version=1, catalog_version=CATALOG.version,
            anchor_set_version=CATALOG.anchor_set_version,
        )
        store.create(view, CATALOG, corpus_member="original-member")
        store.transition(view, Status.CONVERSATION)
        audio = AudioStore(db, tmp_path, actor)
        audio.create(view.id, "conversation_temp", INPUT_RATE, SAMPLE)
        (audio.directory / "orphan.bin").write_bytes(b"fixture")
    with client(Settings(tmp_path)) as session:
        assert practice(session, view.id)["reason_code"] == "SERVER_RESTARTED"
        assert not list((tmp_path / "audio").iterdir())
        manifest = json.loads((tmp_path / "corpus" / view.id / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["member"] == "original-member"
        assert create(session)["id"] != view.id


def test_only_exact_student_quotes_and_matching_anchor_references_publish(tmp_path, monkeypatch):
    original = Simulators.build_report
    tutor_turn = None

    async def draft(self, practice, catalog, results, vocabulary, retry):
        payload = await original(self, practice, catalog, results, vocabulary, retry)
        student = payload["categories"]["vocabulary"]["observations"][0]
        invented = {**student, "id": "invented", "student_quote": "I invented this."}
        tutor = {**student, "id": "tutor", "turn_id": tutor_turn["id"], "student_quote": tutor_turn["text"],
                 "evidence_refs": [tutor_turn["id"]]}
        payload["categories"]["vocabulary"]["observations"] += [invented, tutor]
        payload["categories"]["pronunciation"]["observations"][0]["reference_audio_id"] = "missing-reference"
        return payload

    monkeypatch.setattr(Simulators, "build_report", draft)
    clock = TestClock()
    with client(Settings(tmp_path), clock) as session, started(session) as (view, stream):
        stream.turn()
        stream.get("transcript.updated")
        tutor_turn = stream.get("transcript.updated")["payload"]
        assert tutor_turn["speaker"] == "tutor"
        stream.get("tutor.audio_ended")
        view = anchors(session, clock, view)
        submit_five(session, view, stream)
        wait_for(session, view["id"], "completed")
        report = session.get(f"practices/{view['id']}/report").json()
        assert [item["student_quote"] for item in report["categories"]["vocabulary"]["observations"]] == ["I like this place."]
        assert len(report["categories"]["pronunciation"]["observations"]) == 1
