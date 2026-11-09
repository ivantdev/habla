"""Pruebas del servidor del spike: Origin, negociación, cabecera e interrupción."""
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import server

URL = "/api/v1/practices/p1/stream"
ORIGIN = {"origin": "http://127.0.0.1:8000"}


@pytest.fixture(autouse=True)
def tts_falso(monkeypatch, tmp_path):
    """Sustituye Piper por 2 s de silencio en dos bloques y evita escribir en out/."""
    def synthesize(_text):
        yield bytes(server.OUT_RATE * 2)
        yield bytes(server.OUT_RATE * 2)

    monkeypatch.setattr(server, "synthesize", synthesize)
    monkeypatch.setattr(server, "OUT_DIR", tmp_path)


def event(type_, payload):
    return {"v": 1, "event_id": str(uuid.uuid4()), "practice_id": "p1", "stream_id": None, "seq": 1,
            "occurred_at": "2026-10-30T00:00:00.000Z", "type": type_, "payload": payload}


def open_stream(ws, profile=server.AUDIO_PROFILE_ID):
    ws.send_json(event("stream.open", {"audio_profile_id": profile, "client_instance_id": "c1"}))
    return ws.receive_json()


def frame(stream_id, seq, payload_bytes=server.IN_FRAME_BYTES):
    header = server.pack_header(server.KIND_STUDENT, seq, stream_id, server.NIL, server.NIL)
    return header + bytes(payload_bytes)


def stats(ws):
    ws.send_json(event("spike.stats_request", {}))
    while '"spike.stats"' not in ((msg := ws.receive()).get("text") or ""):
        pass
    return json.loads(msg["text"])["payload"]


def test_voz_ausente_explica_como_descargarla(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "VOICE_PATH", tmp_path / "voices" / "en_US-lessac-medium.onnx")
    monkeypatch.setattr(server, "_voice", None)
    with pytest.raises(SystemExit) as exc:
        server.load_voice()
    assert "piper.download_voices en_US-lessac-medium" in str(exc.value)


def test_cabecera_ida_y_vuelta():
    ids = [uuid.uuid4() for _ in range(3)]
    data = server.pack_header(server.KIND_TUTOR, 7, *ids)
    assert len(data) == server.HEADER.size == 56
    assert server.unpack_header(data) == (1, server.KIND_TUTOR, 7, *ids)


@pytest.mark.parametrize("headers", [{"origin": "http://evil.example"}, {}])
def test_rechaza_origen_no_permitido_o_ausente(headers):
    with pytest.raises(WebSocketDisconnect) as exc:
        with TestClient(server.app).websocket_connect(URL, headers=headers):
            pass
    assert exc.value.code == 1008


def test_acepta_origen_del_proxy():
    with TestClient(server.app).websocket_connect(URL, headers={"origin": "http://127.0.0.1:3000"}) as ws:
        assert open_stream(ws)["type"] == "stream.ready"


def test_negociacion_stream_open_ready():
    with TestClient(server.app).websocket_connect(URL, headers=ORIGIN) as ws:
        msg = open_stream(ws)
    assert msg["type"] == "stream.ready" and msg["v"] == 1 and msg["seq"] == 1
    p = msg["payload"]
    assert set(p) == {"stream_id", "audio_profile_id", "heartbeat_interval_ms", "lease_timeout_ms",
                      "max_frame_bytes", "output_sample_rate_hz"}
    assert p["audio_profile_id"] == "pcm16-v1" and p["output_sample_rate_hz"] == 22050
    assert p["max_frame_bytes"] == 56 + 882
    assert msg["stream_id"] == p["stream_id"]


def test_perfil_no_soportado_rechaza_y_cierra():
    with TestClient(server.app).websocket_connect(URL, headers=ORIGIN) as ws:
        msg = open_stream(ws, profile="opus-48k")
        assert msg["type"] == "stream.rejected"
        assert msg["payload"]["code"] == "UNSUPPORTED_AUDIO_PROFILE"
        assert ws.receive() == {"type": "websocket.close", "code": 1008, "reason": ""}


def test_control_antes_de_abrir_se_rechaza():
    with TestClient(server.app).websocket_connect(URL, headers=ORIGIN) as ws:
        ws.send_json(event("spike.tutor_say", {}))
        msg = ws.receive_json()
        assert msg["type"] == "stream.rejected" and msg["payload"]["code"] == "STREAM_NOT_OPEN"


def test_frames_validos_invalidos_y_huecos():
    with TestClient(server.app).websocket_connect(URL, headers=ORIGIN) as ws:
        sid = uuid.UUID(open_stream(ws)["payload"]["stream_id"])
        for seq in range(3):
            ws.send_bytes(frame(sid, seq))
        ws.send_bytes(frame(uuid.uuid4(), 3))  # stream ajeno
        ws.send_bytes(frame(sid, 3, payload_bytes=100))  # tamaño incorrecto
        ws.send_bytes(frame(sid, 1))  # duplicado
        ws.send_bytes(frame(sid, 5))  # hueco: falta el 3 y el 4
        s = stats(ws)
    assert (s["frames"], s["bad_frames"], s["gaps"]) == (4, 3, 1)
    assert s["audio_ms"] == 80.0


def test_interrupcion_detiene_la_generacion_tras_los_frames_tardios():
    with TestClient(server.app).websocket_connect(URL, headers=ORIGIN) as ws:
        open_stream(ws)
        ws.send_json(event("spike.tutor_say", {"late_frames": 3}))
        started = ws.receive_json()
        assert started["type"] == "tutor.audio_started"
        gen = uuid.UUID(started["payload"]["generation_id"])
        first = ws.receive()["bytes"]
        version, kind, seq, _sid, turn, g = server.unpack_header(first)
        assert (version, kind, seq, g) == (1, server.KIND_TUTOR, 0, gen)
        assert len(first) == 56 + server.OUT_FRAME_BYTES

        ws.send_json(event("student.speech_started", {
            "turn_id": str(uuid.uuid4()), "client_offset_ms": 0,
            "interrupted_generation_id": str(gen), "heard_until_ms": 40}))
        while '"tutor.interrupted"' not in ((msg := ws.receive()).get("text") or ""):
            pass  # frames que ya estaban en vuelo
        interrupted = json.loads(msg["text"])["payload"]
        late = [server.unpack_header(ws.receive()["bytes"])[2] for _ in range(3)]
        ws.send_json(event("spike.stats_request", {}))
        msg = ws.receive()  # no debe llegar ningún otro frame de la generación cancelada
        assert '"spike.stats"' in (msg.get("text") or "")
        s = json.loads(msg["text"])["payload"]
    assert interrupted == {"turn_id": str(turn), "generation_id": str(gen), "heard_until_ms": 40}
    assert late == list(range(late[0], late[0] + 3))
    assert s["interrupts"][0]["late_frames"] == 3
    # 2 s de audio son 100 frames; tras la interrupción no se envió el resto.
    assert s["interrupts"][0]["frames_sent_before"] + 3 < 100
