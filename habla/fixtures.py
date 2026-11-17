"""Datos sintéticos para desarrollar con C-08. El catálogo final pertenece a B."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import math
import struct

from .audio import wav_bytes, INPUT_RATE
from .contracts import (
    AccountView, AnchorPhrase, AudioAsset, Catalog, ConsentRecord,
    ErrorBody, ErrorEnvelope, ObjectivesByLevel, Practice, Status, Topic, TopicObjectives,
)
from .identity import BASE_CONSENT_ID, BASE_OWNER_ID


CATALOG = Catalog(
    version="fixture-catalog-v1",
    levels=["A2", "B1", "B2"],
    topics=[
        Topic(
            id=topic_id, label_es=label,
            objectives_by_level=ObjectivesByLevel(**{
                level: TopicObjectives(
                    scenario_en=f"Practice talking about {context}.",
                    vocabulary=[context], structures=["I would like ..."], starter_questions=[question],
                ) for level in ("A2", "B1", "B2")
            }),
        )
        for topic_id, label, context, question in [
            ("restaurant", "Restaurante", "food", "What would you like to order?"),
            ("job_interview", "Entrevista laboral", "work", "What do you enjoy about your work?"),
            ("weekend", "Fin de semana", "plans", "What do you like to do on weekends?"),
            ("travel", "Viajes", "travel", "Where would you like to travel?"),
            ("news", "Noticias", "local news", "What is happening in your town?"),
        ]
    ],
    anchor_set_version="fixture-anchors-v1",
    anchors=[
        AnchorPhrase(
            id=f"fixture-anchor-{position}", position=position, text_en=text,
            reference_audio_id=f"fixture-reference-{position}", target_sounds=[sound],
        )
        for position, (text, sound) in enumerate([
            ("I think this train is fast.", "θ"),
            ("Three friends went to the park.", "θ"),
            ("She sells fresh fish.", "ʃ"),
            ("The red car is near the river.", "ɹ"),
            ("Would you like a glass of water?", "w"),
        ], start=1)
    ],
    tutor_policy_version="fixture-policy-v1",
    tutor_policy="Política simulada C-08 para probar el intercambio de turnos.",
)


def tone(rate: int, frequency: int, duration_ms: int) -> bytes:
    frames = (int(1600 * math.sin(2 * math.pi * frequency * index / rate))
              for index in range(rate * duration_ms // 1000))
    return b"".join(struct.pack("<h", sample) for sample in frames)


REFERENCES = {
    item.reference_audio_id: wav_bytes(tone(INPUT_RATE, 330 + item.position * 40, 320), INPUT_RATE)
    for item in CATALOG.anchors
}


def platform_examples() -> dict:
    stamp = datetime(2026, 10, 30, tzinfo=timezone.utc)
    identity = AccountView(id=BASE_OWNER_ID, email="equipo@habla.invalid", created_at=stamp)
    consent = ConsentRecord(
        id=BASE_CONSENT_ID, owner_id=identity.id, policy_version="d18-fixture-v1",
        accepted_at=stamp, external_processors=[],
    )
    practices = [
        Practice(
            id=f"fixture-practice-{status}", created_at=stamp,
            level="A2", topic_id="restaurant", duration_seconds=300, status=status,
            state_version=version, catalog_version=CATALOG.version, anchor_set_version=CATALOG.anchor_set_version,
            conversation_started_at=stamp if version > 1 else None,
            conversation_ends_at=stamp + timedelta(seconds=300) if version > 1 else None,
            report_id="fixture-report-1" if status == Status.COMPLETED else None,
            evaluator_version="fixture-evaluator-v1" if status == Status.COMPLETED else None,
            reason_code="CANCELLED" if status == Status.INCOMPLETE else None,
        )
        for version, status in enumerate(Status, start=1)
    ]
    assets = [
        AudioAsset(
            id=f"fixture-audio-{source}", practice_id=f"fixture-practice-{phase}",
            source=source, captured_at=stamp, status=status, duration_ms=320, media_type=media_type,
        )
        for source, phase, status, media_type in [
            ("conversation_temp", Status.CONVERSATION, "pending", "application/octet-stream"),
            ("anchor", Status.COMPLETED, "available", "audio/wav"),
        ]
    ]
    busy = ErrorEnvelope(error=ErrorBody(
        code="SERVER_BUSY", message="El servidor está ocupado. Intenta de nuevo.",
        request_id="fixture-request-1", retryable=True,
    ))
    return {
        "contract_version": "1",
        "simulation": True,
        "account": identity.model_dump(mode="json"),
        "consent": consent.model_dump(mode="json"),
        "practices": [practice.model_dump(mode="json") for practice in practices],
        "audio_assets": [asset.model_dump(mode="json") for asset in assets],
        "busy": busy.model_dump(mode="json"),
    }


FIXTURE_PATH = Path(__file__).resolve().parent.parent / "contracts" / "fixtures" / "platform-v1.json"


def fixture_text() -> str:
    return json.dumps(platform_examples(), ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(fixture_text(), encoding="utf-8")
