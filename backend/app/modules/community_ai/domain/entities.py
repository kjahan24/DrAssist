"""Community AI Features module aggregate: `AICommunityAnalysis`.

**The first job-execution-status aggregate in this codebase.** Every
prior AI-feature module (`icd10_ai`, `medical_reasoning_ai`,
`drug_interaction_ai`, ...) calls its AI provider synchronously, inline,
within one request/response cycle, and persists nothing — see each
module's own `container.py` scope note (e.g. `medical_reasoning_ai
.container`: "this task builds a generation-only, reasoning-only module
... and never persists"). This module is the first to actually persist
an AI analysis with a `PENDING -> PROCESSING -> COMPLETED | FAILED`
lifecycle, because `GetAIAnalysis`/`ListAIAnalyses`/`RefreshAIAnalysis`
(this task's own APPLICATION section) only make sense against a durable
record — and because persisting the result is also what "Avoid
unnecessary repeated AI calls" (this task's own CACHING/PERFORMANCE
section) is built on: a fresh `COMPLETED` row is itself the cache: no
separate Redis-backed caching layer exists anywhere in this codebase for
AI results to reuse (confirmed absent), so the persisted analysis row
*is* the caching mechanism.

One row per `(target_type, target_id, analysis_type)` — `RefreshAIAnalysis`
transitions the *same* row back through `PROCESSING` and overwrites its
own `result`/`confidence_score`/`ai_provider`/`ai_model` in place, never
inserting a second row for a target that was already analyzed, mirroring
`app.modules.community_engagement.domain.entities.Vote.switch()`'s own
"one row per identity, mutated in place, never delete-then-recreate"
precedent — see `infrastructure/models.py`'s own docstring for the unique
constraint that makes this the enforced shape, not just a convention.

`result`/`confidence_score`/`ai_provider`/`ai_model` are all `None` until
`mark_completed()` — a `PENDING`/`PROCESSING`/`FAILED` row genuinely has
no result yet, so `None` is the correct, honest representation rather
than an empty placeholder value.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.events import (
    AIAnalysisCompleted,
    AIAnalysisFailed,
    AIAnalysisRequested,
)
from app.modules.community_ai.domain.exceptions import (
    AnalysisAlreadyProcessingError,
    AnalysisNotProcessingError,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class AICommunityAnalysis(AggregateRoot):
    organization_id: UUID
    analysis_type: AIAnalysisType
    target_type: CommunityContentTargetType
    target_id: UUID
    status: AIAnalysisStatus = AIAnalysisStatus.PENDING
    result: dict[str, Any] | None = None
    confidence_score: float | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    error_message: str | None = None
    latency_ms: float | None = None

    @classmethod
    def request(
        cls,
        *,
        organization_id: UUID,
        analysis_type: AIAnalysisType,
        target_type: CommunityContentTargetType,
        target_id: UUID,
    ) -> "AICommunityAnalysis":
        analysis = cls(
            organization_id=organization_id,
            analysis_type=analysis_type,
            target_type=target_type,
            target_id=target_id,
        )
        analysis.record_event(
            AIAnalysisRequested(
                analysis_id=analysis.id,
                analysis_type=analysis_type,
                target_type=target_type,
                target_id=target_id,
            )
        )
        return analysis

    def mark_processing(self) -> None:
        """Allowed from `PENDING`, `COMPLETED`, or `FAILED` — the latter
        two are exactly the `RefreshAIAnalysis` re-run path. Only
        `PROCESSING` itself is rejected, guarding against a concurrent
        double-dispatch of the same analysis."""
        if self.status is AIAnalysisStatus.PROCESSING:
            raise AnalysisAlreadyProcessingError(self.id)
        self.status = AIAnalysisStatus.PROCESSING
        self.error_message = None
        self.touch()

    def mark_completed(
        self,
        *,
        result: dict[str, Any],
        confidence_score: float | None,
        ai_provider: str,
        ai_model: str,
        latency_ms: float | None = None,
    ) -> None:
        if self.status is not AIAnalysisStatus.PROCESSING:
            raise AnalysisNotProcessingError(self.id)
        self.status = AIAnalysisStatus.COMPLETED
        self.result = result
        self.confidence_score = confidence_score
        self.ai_provider = ai_provider
        self.ai_model = ai_model
        self.latency_ms = latency_ms
        self.error_message = None
        self.touch()
        self.record_event(
            AIAnalysisCompleted(
                analysis_id=self.id,
                analysis_type=self.analysis_type,
                target_type=self.target_type,
                target_id=self.target_id,
            )
        )

    def mark_failed(self, error_message: str) -> None:
        if self.status is not AIAnalysisStatus.PROCESSING:
            raise AnalysisNotProcessingError(self.id)
        self.status = AIAnalysisStatus.FAILED
        self.error_message = error_message
        self.touch()
        self.record_event(
            AIAnalysisFailed(
                analysis_id=self.id,
                analysis_type=self.analysis_type,
                target_type=self.target_type,
                target_id=self.target_id,
                error_message=error_message,
            )
        )
