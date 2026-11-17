"""Adaptadores de desarrollo de B/C. Solo consumen PCM sintético en la demo web."""

from dataclasses import dataclass
from uuid import uuid5, NAMESPACE_URL
import asyncio

from .audio import Recording
from .contracts import (
    AnchorAttempt, AnchorPhrase, Category, Categories, Catalog, Coverage, Evidence,
    Observation, PhoneticResult, Practice, Report, Turn, utc_now,
)
from .errors import PlatformError
from .fixtures import tone
from .report_validation import CONVERSATION_LIMITATION, summarize


TUTOR_RATE = 22_050
EVALUATOR_VERSION = "fixture-evaluator-v1"
VALIDITY_VERSION = "fixture-validity-v1"
CALIBRATION_VERSION = "fixture-calibration-v1"


def fixture_id(*values: str) -> str:
    return str(uuid5(NAMESPACE_URL, "/".join(values)))


@dataclass(frozen=True)
class Simulators:
    scenario: str

    def fault(self, stage: str, retry: bool) -> None:
        if (self.scenario == f"{stage}_fail_once" and not retry) or (
            stage == "report" and self.scenario == "report_unavailable"
        ):
            raise PlatformError(
                503, f"{stage.upper()}_UNAVAILABLE", "Falló una operación simulada.", retryable=True,
            )

    async def asr(self, pcm: bytes, retry: bool) -> str:
        self.fault("asr", retry)
        return "I like this place." if any(pcm) else ""

    async def tutor(self, practice: Practice, catalog: Catalog, retry: bool) -> str:
        self.fault("tutor", retry)
        topic = next(topic for topic in catalog.topics if topic.id == practice.topic_id)
        return getattr(topic.objectives_by_level, practice.level).starter_questions[0]

    async def tts(self, text: str, retry: bool) -> bytes:
        self.fault("tts", retry)
        return tone(TUTOR_RATE, 400 + len(text), 320)

    async def validate_anchor(self, wav_data: bytes, retry: bool) -> str | None:
        self.fault("anchor", retry)
        if self.scenario == "anchor_invalid" or len(wav_data) < 6444 or not any(wav_data[44:]):
            return "NO_USABLE_SPEECH"
        return None

    async def evaluate(
        self, practice: Practice, phrase: AnchorPhrase, recording: Recording,
    ) -> PhoneticResult:
        if self.scenario == "slow_evaluation":
            await asyncio.sleep(0.5)
        asset = recording.asset
        sound = phrase.target_sounds[0]
        unit_id = fixture_id(asset.id, "unit")
        end = min(120, asset.duration_ms)
        has_error = phrase.position in (1, 3)
        return PhoneticResult(
            id=fixture_id(asset.id, "result"), practice_id=practice.id, source_audio_id=asset.id,
            source_kind="anchor", anchor_phrase_id=phrase.id, evaluator_version=EVALUATOR_VERSION,
            calibration_version=CALIBRATION_VERSION, anchor_set_version=practice.anchor_set_version,
            coverage=[Coverage(
                unit_id=unit_id, start_ms=0, end_ms=end, expected_sound=sound,
                status="not_evaluated" if phrase.position == 2 else "evaluated",
                reason="FIXTURE_EXCLUDED" if phrase.position == 2 else None,
            )],
            evidence=[Evidence(
                id=fixture_id(asset.id, "evidence"), unit_id=unit_id, start_ms=0, end_ms=end,
                expected_sound=sound, error_type="FIXTURE_SUBSTITUTION", confidence=0.9,
                decision_threshold=0.7, method="fixture",
            )] if has_error else [],
        )

    async def linguistic(self, turns: list[Turn]) -> Category:
        student = next((turn for turn in turns if turn.speaker == "student" and turn.status == "final"), None)
        if student is None or not student.text:
            return Category(status="not_evaluated", observations=[])
        return Category(status="observations", observations=[Observation(
            id=fixture_id(student.id, "vocabulary"), category="vocabulary",
            explanation_es="Ejemplo simulado. Prueba a describir el lugar con un adjetivo.",
            evidence_refs=[student.id], student_quote=student.text, turn_id=student.id,
        )])

    async def build_report(
        self, practice: Practice, catalog: Catalog, results: list[PhoneticResult],
        vocabulary: Category, retry: bool,
    ) -> dict:
        self.fault("report", retry)
        phrases = {phrase.id: phrase for phrase in catalog.anchors}
        observations = [
            Observation(
                id=fixture_id(item.id, "observation"), category="pronunciation",
                explanation_es=f"Ejemplo simulado. Escucha el intervalo para practicar /{item.expected_sound}/.",
                evidence_refs=[item.id], audio_id=result.source_audio_id, reference_scope="catalog",
                reference_audio_id=phrases[result.anchor_phrase_id].reference_audio_id,
                playback_start_ms=item.start_ms, playback_end_ms=item.end_ms,
            )
            for result in results for item in result.evidence
        ]
        return Report(
            id=fixture_id(practice.id, "report"), practice_id=practice.id, language="es",
            created_at=utc_now(), schema_version="1", evaluator_version=EVALUATOR_VERSION,
            anchor_set_version=practice.anchor_set_version,
            categories=Categories(
                pronunciation=Category(status="observations" if observations else "no_supported_observations",
                                       observations=observations),
                grammar=Category(
                    status="not_evaluated" if vocabulary.status == "not_evaluated" else "no_supported_observations",
                    observations=[],
                ),
                vocabulary=vocabulary,
            ),
            limitations=[CONVERSATION_LIMITATION, "Informe simulado con audio y evidencia sintéticos."],
            anchor_summary=summarize(results),
        ).model_dump(mode="json")
