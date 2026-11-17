"""Proyección autorizada y comparación de SPEC-10."""

import base64
import binascii
import hashlib
import json

from .audio import AudioStore
from .contracts import Comparison, HistoryPage, PracticeSummary, SoundComparison, SoundCounts
from .errors import PlatformError
from .storage import Draft, PracticeStore


class History:
    def __init__(self, store: PracticeStore, audio: AudioStore):
        self.store = store
        self.audio = audio

    def page(self, limit: int, cursor: str | None) -> HistoryPage:
        after = None
        if cursor:
            try:
                key = base64.b64decode(cursor, altchars=b"-_", validate=True).decode("ascii")
            except (UnicodeError, binascii.Error, ValueError) as error:
                raise PlatformError(400, "INVALID_CURSOR", "El cursor del historial no es válido.") from error
            after = self.store.get(key)
        rows = self.store.history(limit + 1, after)
        items = [
            PracticeSummary(
                id=view.id, date=view.created_at, topic_id=view.topic_id, level=view.level, status=view.status,
                report_available=self.store.published(view) is not None,
                audio_availability="available" if self.audio.available_anchors(view) else "unavailable",
            )
            for view in rows[:limit]
        ]
        next_cursor = base64.urlsafe_b64encode(items[-1].id.encode("ascii")).decode("ascii") if len(rows) > limit else None
        return HistoryPage(items=items, next_cursor=next_cursor)

    def compare(self, left_id: str, right_id: str) -> Comparison:
        left = self.store.published(self.store.get(left_id))
        right = self.store.published(self.store.get(right_id))
        if left_id == right_id or left is None or right is None:
            raise PlatformError(409, "INCOMPATIBLE_SESSIONS", "Elige dos prácticas distintas y completadas.")
        versions = self._versions(left)
        if versions != self._versions(right):
            raise PlatformError(409, "INCOMPATIBLE_SESSIONS", "Las versiones de frases o de evaluación son distintas.")
        left_counts, right_counts = self._counts(left), self._counts(right)
        return Comparison(
            left_id=left_id, right_id=right_id, compatible=True,
            compatibility_key=hashlib.sha256(json.dumps(versions).encode()).hexdigest(),
            sounds=[
                SoundComparison(
                    sound=sound, left=left_counts.get(sound, SoundCounts()), right=right_counts.get(sound, SoundCounts()),
                )
                for sound in sorted(left_counts.keys() | right_counts.keys())
            ],
            limitations=[
                "Comparación simulada de las cinco frases ancla.",
                "Las oportunidades sin evaluar se muestran por separado.",
            ],
        )

    @staticmethod
    def _versions(draft: Draft) -> tuple[str, str, str]:
        return draft.report.anchor_set_version, draft.report.evaluator_version, draft.calibration

    @staticmethod
    def _counts(draft: Draft) -> dict[str, SoundCounts]:
        counts: dict[str, SoundCounts] = {}
        for row in draft.report.anchor_summary:
            prior = counts.get(row.sound, SoundCounts())
            counts[row.sound] = SoundCounts(
                evaluated_opportunities=prior.evaluated_opportunities + row.evaluated_opportunities,
                detected_errors=prior.detected_errors + row.detected_errors,
                not_evaluated_opportunities=prior.not_evaluated_opportunities + row.not_evaluated_opportunities,
            )
        return counts
