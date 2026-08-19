"""Application-layer DTOs for the Community AI Features module.

Input DTOs carry an explicit `organization_id`/`requester_id` field for
the same reason `app.modules.community_moderation.application.dto`'s own
Input DTOs do: AI analysis has no community-membership-style "get it for
free" tenant check the way content-creation modules do, so tenant/
visibility comparison is threaded through explicitly wherever a target is
resolved — see `services/_authorization.py`'s own docstring.

`GenerationMetadata` is the ephemeral (never independently persisted)
provider/model/latency envelope one AI call produces — mirrors
`app.modules.medical_reasoning_ai`'s own `GenerationSession` value object;
unlike that precedent, this module's `AICommunityAnalysisSummaryDTO` DOES
persist the `provider`/`model` fields (on `AICommunityAnalysis` itself),
since this task's own PERSISTENCE section explicitly asks for
"model/provider metadata" to be stored.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.value_objects import SimilarDiscussion

# --- Shared -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenerationMetadata:
    provider: str
    model: str
    latency_ms: float


@dataclass(frozen=True, slots=True)
class AICommunityAnalysisSummaryDTO:
    analysis_id: UUID
    organization_id: UUID
    analysis_type: AIAnalysisType
    target_type: CommunityContentTargetType
    target_id: UUID
    status: AIAnalysisStatus
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None
    confidence_score: float | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    error_message: str | None = None
    latency_ms: float | None = None

    @property
    def id(self) -> UUID:
        return self.analysis_id


# --- Generate / refresh requests --------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenerateDiscussionSummaryInput:
    organization_id: UUID
    requester_id: UUID
    target_type: CommunityContentTargetType
    target_id: UUID


@dataclass(frozen=True, slots=True)
class FindSimilarDiscussionsInput:
    organization_id: UUID
    requester_id: UUID
    target_type: CommunityContentTargetType
    target_id: UUID
    cursor: str | None = None
    limit: int = 10


@dataclass(frozen=True, slots=True)
class RecommendTrustedResourcesInput:
    organization_id: UUID
    requester_id: UUID
    target_type: CommunityContentTargetType
    target_id: UUID


@dataclass(frozen=True, slots=True)
class AnalyzeMisinformationInput:
    organization_id: UUID
    requester_id: UUID
    target_type: CommunityContentTargetType
    target_id: UUID


@dataclass(frozen=True, slots=True)
class RefreshAIAnalysisInput:
    organization_id: UUID
    requester_id: UUID
    analysis_id: UUID


# --- Queries ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GetAIAnalysisInput:
    organization_id: UUID
    analysis_id: UUID


@dataclass(frozen=True, slots=True)
class ListAIAnalysesInput:
    organization_id: UUID
    target_type: CommunityContentTargetType | None = None
    target_id: UUID | None = None
    analysis_type: AIAnalysisType | None = None
    status: AIAnalysisStatus | None = None
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class AnalysisFeedOutput:
    items: list[AICommunityAnalysisSummaryDTO]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class SimilarDiscussionFeedOutput:
    analysis_id: UUID
    items: list[SimilarDiscussion]
    next_cursor: str | None = None
