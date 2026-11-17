"""Barrera de publicación del rol A (S09-CA-02, S09-CA-03, C-06 y C-09)."""

from collections import Counter
from logging import getLogger
import json

from pydantic import ValidationError

from .contracts import (
    AnchorAttempt, AnchorSummary, Categories, Category, Catalog, PhoneticResult, Practice, Report, Turn,
)
from .errors import PlatformError
from .storage import Draft


CONVERSATION_LIMITATION = "La pronunciación de la conversación no se evaluó."
logger = getLogger("uvicorn.error.habla")


def invalid_report() -> PlatformError:
    return PlatformError(503, "REPORT_INVALID", "No se pudo validar el informe.", retryable=True)


def summarize(results: list[PhoneticResult]) -> list[AnchorSummary]:
    rows = []
    for result in results:
        evaluated = Counter()
        excluded = Counter()
        errors = Counter()
        error_units = {item.unit_id for item in result.evidence}
        for unit in result.coverage:
            if unit.expected_sound is None:
                continue
            if unit.status == "evaluated":
                evaluated[unit.expected_sound] += 1
                errors[unit.expected_sound] += unit.unit_id in error_units
            else:
                excluded[unit.expected_sound] += 1
        for sound in sorted(evaluated.keys() | excluded.keys()):
            rows.append(AnchorSummary(
                phrase_id=result.anchor_phrase_id, sound=sound, evaluated_opportunities=evaluated[sound],
                detected_errors=errors[sound], not_evaluated_opportunities=excluded[sound],
            ))
    return rows


def validate_draft(
    payload: dict, results: list[PhoneticResult], practice: Practice, catalog: Catalog,
    attempts: list[AnchorAttempt], durations: dict[str, int], turns: list[Turn],
    references: set[str],
) -> Draft:
    try:
        report = Report.model_validate_json(json.dumps(payload))
    except ValidationError as error:
        raise invalid_report() from error
    phrases = {phrase.id: phrase for phrase in catalog.anchors}
    anchors = {attempt.audio_id: attempt for attempt in attempts if attempt.status == "valid"}
    if (
        len(anchors) != 5 or {attempt.phrase_id for attempt in anchors.values()} != phrases.keys()
        or len(results) != 5 or {result.source_audio_id for result in results} != anchors.keys()
        or len({result.calibration_version for result in results}) != 1
        or report.practice_id != practice.id or report.anchor_set_version != practice.anchor_set_version
        or any(result.evaluator_version != report.evaluator_version for result in results)
    ):
        raise invalid_report()

    evidence = {}
    for result in results:
        audio_id = result.source_audio_id
        phrase = phrases[anchors[audio_id].phrase_id]
        if (
            result.practice_id != practice.id or result.source_kind != "anchor"
            or result.anchor_phrase_id != phrase.id or result.anchor_set_version != practice.anchor_set_version
            or audio_id not in durations
        ):
            raise invalid_report()
        units = {unit.unit_id: unit for unit in result.coverage}
        if len(units) != len(result.coverage) or any(
            not 0 <= unit.start_ms < unit.end_ms <= durations[audio_id] for unit in units.values()
        ):
            raise invalid_report()
        for item in result.evidence:
            unit = units.get(item.unit_id)
            if (
                unit is None or unit.status != "evaluated" or item.id in evidence
                or item.expected_sound != unit.expected_sound
                or not unit.start_ms <= item.start_ms < item.end_ms <= unit.end_ms
            ):
                raise invalid_report()
            evidence[item.id] = (audio_id, phrase.reference_audio_id, item.start_ms, item.end_ms)

    final_student = {
        turn.id: turn.text for turn in turns
        if turn.speaker == "student" and turn.status == "final" and turn.practice_id == practice.id
    }
    categories = {}
    for name in ("pronunciation", "grammar", "vocabulary"):
        category = getattr(report.categories, name)
        supported = []
        for item in category.observations:
            if item.category != name or category.status != "observations":
                continue
            if name == "pronunciation":
                start, end = item.playback_start_ms, item.playback_end_ms
                valid = (
                    item.reference_scope == "catalog" and item.reference_audio_id in references
                    and start is not None and end is not None
                    and 0 <= start < end <= durations.get(item.audio_id, 0)
                    and bool(item.evidence_refs)
                    and all(
                        (linked := evidence.get(ref)) is not None
                        and linked[:2] == (item.audio_id, item.reference_audio_id)
                        and start <= linked[2] < linked[3] <= end
                        for ref in item.evidence_refs
                    )
                )
            else:
                valid = bool(
                    item.student_quote and item.student_quote.strip()
                    and item.student_quote in final_student.get(item.turn_id, "")
                    and item.turn_id in item.evidence_refs
                    and all(ref == item.turn_id for ref in item.evidence_refs)
                    and item.audio_id is None and item.reference_audio_id is None and item.reference_scope is None
                )
            if valid:
                supported.append(item)
        if rejected := len(category.observations) - len(supported):
            logger.info("report_observations_filtered category=%s count=%d", name, rejected)
        status = category.status
        if not supported and status == "observations":
            status = "no_supported_observations"
        categories[name] = Category(status=status, observations=supported)

    summary = summarize(results)
    valid_counts = {(row.phrase_id, row.sound): row for row in summary}
    proposed_counts = {(row.phrase_id, row.sound): row for row in report.anchor_summary}
    if valid_counts != proposed_counts or len(proposed_counts) != len(report.anchor_summary):
        raise invalid_report()
    if not any(row.evaluated_opportunities for row in summary):
        categories["pronunciation"] = Category(status="not_evaluated", observations=[])
    limitations = list(dict.fromkeys([*report.limitations, CONVERSATION_LIMITATION]))
    return Draft(report.model_copy(update={"categories": Categories(**categories), "limitations": limitations}), results)
