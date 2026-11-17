"""DTO de C-01 a C-06. El consumidor web usa el JSON Schema de estos modelos."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, AwareDatetime


Identifier = Annotated[str, StringConstraints(min_length=1, max_length=128)]
Count = Annotated[int, Field(ge=0)]
Version = Annotated[int, Field(ge=1)]
Level = Literal["A2", "B1", "B2"]
TopicId = Literal["restaurant", "job_interview", "weekend", "travel", "news"]
Duration = Literal[300, 600]
CategoryName = Literal["pronunciation", "grammar", "vocabulary"]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Status(StrEnum):
    READY = "ready"
    CONVERSATION = "conversation"
    ANCHORS = "anchors"
    PROCESSING = "processing"
    ERROR = "recoverable_error"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ErrorBody(DTO):
    code: str
    message: str
    request_id: Identifier
    retryable: bool
    details: dict | None = None


class ErrorEnvelope(DTO):
    error: ErrorBody


class AccountView(DTO):
    id: Identifier
    email: str
    created_at: AwareDatetime


class ConsentPolicy(DTO):
    version: Identifier
    purposes: list[str]
    retention_days: Literal[30]
    external_processors: list[str]


class ConsentRecord(DTO):
    id: Identifier
    owner_id: Identifier
    policy_version: Identifier
    accepted_at: AwareDatetime
    external_processors: list[str]


class TopicObjectives(DTO):
    scenario_en: str
    vocabulary: list[str]
    structures: list[str]
    starter_questions: list[str]


class ObjectivesByLevel(DTO):
    A2: TopicObjectives
    B1: TopicObjectives
    B2: TopicObjectives


class Topic(DTO):
    id: TopicId
    label_es: str
    objectives_by_level: ObjectivesByLevel


class AnchorPhrase(DTO):
    id: Identifier
    position: Annotated[int, Field(ge=1, le=5)]
    text_en: str
    reference_audio_id: Identifier
    target_sounds: list[str]


class Catalog(DTO):
    version: Identifier
    levels: list[Level]
    topics: list[Topic]
    anchor_set_version: Identifier
    anchors: Annotated[list[AnchorPhrase], Field(min_length=5, max_length=5)]
    tutor_policy_version: Identifier
    tutor_policy: str


class CreatePractice(DTO):
    level: Level
    topic_id: TopicId
    duration_seconds: Duration
    consent_id: Identifier | None = None
    catalog_version: Identifier


class StateCommand(DTO):
    state_version: Version


class RetryCommand(StateCommand):
    operation_id: Identifier


class Practice(DTO):
    id: Identifier
    created_at: AwareDatetime
    level: Level
    topic_id: TopicId
    duration_seconds: Duration
    status: Status
    state_version: Version
    reason_code: str | None = None
    conversation_started_at: AwareDatetime | None = None
    conversation_ends_at: AwareDatetime | None = None
    catalog_version: Identifier
    anchor_set_version: Identifier
    evaluator_version: Identifier | None = None
    report_id: Identifier | None = None


class Operation(DTO):
    id: Identifier
    type: str
    status: Literal["pending", "running", "succeeded", "failed"]
    resource_id: Identifier | None = None
    error: ErrorBody | None = None


class AudioAsset(DTO):
    id: Identifier
    practice_id: Identifier | None = None
    source: Literal["conversation_temp", "anchor", "conversation_clip", "reference", "clip_reference"]
    captured_at: AwareDatetime
    expires_at: AwareDatetime | None = None
    status: Literal["pending", "available", "expired", "deleted"]
    media_type: str
    duration_ms: Count
    source_asset_id: Identifier | None = None
    source_start_ms: Count | None = None
    source_end_ms: Count | None = None


class Turn(DTO):
    id: Identifier
    practice_id: Identifier
    sequence: Count
    speaker: Literal["student", "tutor"]
    text: str
    status: Literal["partial", "final", "interrupted"]
    audio_id: Identifier | None = None
    start_ms: Count
    end_ms: Count
    word_confidence: list[float] | None = None
    heard_until_ms: Count | None = None


class AnchorAttempt(DTO):
    id: Identifier
    practice_id: Identifier
    phrase_id: Identifier
    attempt_number: Annotated[int, Field(ge=1, le=3)]
    audio_id: Identifier
    status: Literal["pending", "valid", "invalid"]
    invalid_reason: str | None = None
    validity_version: Identifier


class AttemptList(DTO):
    items: Annotated[list[AnchorAttempt], Field(max_length=15)]


class StreamOpen(DTO):
    audio_profile_id: Identifier
    client_instance_id: Identifier


class StreamReady(DTO):
    stream_id: Identifier
    audio_profile_id: Identifier
    heartbeat_interval_ms: Count
    lease_timeout_ms: Count
    max_frame_bytes: Count
    output_sample_rate_hz: Count


class Event(DTO):
    v: Literal[1]
    event_id: Identifier
    practice_id: Identifier
    stream_id: Identifier | None
    seq: Count
    occurred_at: AwareDatetime
    type: Identifier
    payload: dict


class Coverage(DTO):
    unit_id: Identifier
    start_ms: Count
    end_ms: Count
    expected_sound: str | None = None
    status: Literal["evaluated", "not_evaluated"]
    reason: str | None = None


class Evidence(DTO):
    id: Identifier
    unit_id: Identifier
    start_ms: Count
    end_ms: Count
    expected_sound: str
    observed_sound: str | None = None
    error_type: str
    confidence: float
    decision_threshold: float
    method: Identifier


class PhoneticResult(DTO):
    id: Identifier
    practice_id: Identifier
    source_audio_id: Identifier
    source_kind: Literal["anchor", "conversation_temp"]
    anchor_phrase_id: Identifier | None = None
    evaluator_version: Identifier
    calibration_version: Identifier
    anchor_set_version: Identifier | None = None
    coverage: list[Coverage]
    evidence: list[Evidence]


class Observation(DTO):
    id: Identifier
    category: CategoryName
    explanation_es: str
    evidence_refs: list[Identifier]
    student_quote: str | None = None
    turn_id: Identifier | None = None
    audio_id: Identifier | None = None
    reference_audio_id: Identifier | None = None
    reference_scope: Literal["catalog", "practice"] | None = None
    playback_start_ms: Count | None = None
    playback_end_ms: Count | None = None


class Category(DTO):
    status: Literal["observations", "no_supported_observations", "not_evaluated"]
    observations: list[Observation]


class Categories(DTO):
    pronunciation: Category
    grammar: Category
    vocabulary: Category


class AnchorSummary(DTO):
    phrase_id: Identifier
    sound: str
    evaluated_opportunities: Count
    detected_errors: Count
    not_evaluated_opportunities: Count


class Report(DTO):
    id: Identifier
    practice_id: Identifier
    language: Literal["es"]
    created_at: AwareDatetime
    schema_version: Literal["1"]
    evaluator_version: Identifier
    anchor_set_version: Identifier
    categories: Categories
    limitations: list[str]
    anchor_summary: list[AnchorSummary]


class PracticeSummary(DTO):
    id: Identifier
    date: AwareDatetime
    topic_id: TopicId
    level: Level
    status: Status
    report_available: bool
    audio_availability: Literal["available", "unavailable"]


class HistoryPage(DTO):
    items: list[PracticeSummary]
    next_cursor: str | None


class SoundCounts(DTO):
    evaluated_opportunities: Count = 0
    detected_errors: Count = 0
    not_evaluated_opportunities: Count = 0


class SoundComparison(DTO):
    sound: str
    left: SoundCounts
    right: SoundCounts


class Comparison(DTO):
    left_id: Identifier
    right_id: Identifier
    compatible: Literal[True]
    compatibility_key: Identifier
    sounds: list[SoundComparison]
    limitations: list[str]


CONTRACT_MODELS = [
    ErrorEnvelope, AccountView, ConsentPolicy, ConsentRecord, Catalog, CreatePractice, StateCommand,
    RetryCommand, Practice, Operation, AudioAsset, Turn, AnchorAttempt, AttemptList, Event, StreamOpen, StreamReady,
    PhoneticResult, Report, HistoryPage, Comparison,
]
