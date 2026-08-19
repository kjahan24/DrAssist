"""Pydantic v2 response schemas for the Community AI Features module's
REST API. Every schema here mirrors an application-layer summary DTO
one-to-one via `model_validate(..., from_attributes=True)`, the same
"response schema, not a domain type" split every prior module's own
`presentation/schemas.py` establishes.

`AICommunityAnalysisResponse.ai_disclaimer` is a fixed, non-AI-controlled
constant (a Pydantic default, never populated from the DTO) — the
structural half of this task's own SAFETY requirement "Clearly
distinguish AI-generated analysis from verified medical information":
every response carries it regardless of whether the underlying `result`
JSON also happens to include its own AI-generated
`safety_disclaimer`/`explanation` text (see `domain/value_objects.py`'s
own docstring), so the distinction never depends on the model complying
with a prompt instruction.

No request body schemas are needed for `summary`/`resources`/
`misinformation`/`refresh` — every field their application-layer Input
DTOs need (`organization_id`, `requester_id`, `target_type`, `target_id`)
comes from the path and `CurrentUser`, matching the same "no body needed"
shape `community_engagement.presentation.router`'s own vote-toggle
endpoints already use.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)

_AI_DISCLAIMER = (
    "This is AI-generated analysis, not verified medical information. "
    "It is never a diagnosis or a treatment recommendation, and should "
    "not replace professional medical advice."
)


class AICommunityAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
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
    ai_disclaimer: str = _AI_DISCLAIMER


class AICommunityAnalysisFeedResponse(BaseModel):
    items: list[AICommunityAnalysisResponse]
    next_cursor: str | None = None


class SimilarDiscussionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_type: CommunityContentTargetType
    target_id: UUID
    similarity_score: float


class SimilarDiscussionFeedResponse(BaseModel):
    analysis_id: UUID
    items: list[SimilarDiscussionResponse]
    next_cursor: str | None = None
    ai_disclaimer: str = _AI_DISCLAIMER
