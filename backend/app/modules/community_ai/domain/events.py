"""Domain events for the Community AI Features module. All
`@dataclass(frozen=True, kw_only=True)` subclasses of `DomainEvent` — see
that base class's own docstring."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_ai.domain.enums import (
    AIAnalysisType,
    CommunityContentTargetType,
    MisinformationRiskLevel,
)
from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AIAnalysisRequested(DomainEvent):
    analysis_id: UUID
    analysis_type: AIAnalysisType
    target_type: CommunityContentTargetType
    target_id: UUID


@dataclass(frozen=True, kw_only=True)
class AIAnalysisCompleted(DomainEvent):
    analysis_id: UUID
    analysis_type: AIAnalysisType
    target_type: CommunityContentTargetType
    target_id: UUID


@dataclass(frozen=True, kw_only=True)
class AIAnalysisFailed(DomainEvent):
    analysis_id: UUID
    analysis_type: AIAnalysisType
    target_type: CommunityContentTargetType
    target_id: UUID
    error_message: str


@dataclass(frozen=True, kw_only=True)
class HighRiskMisinformationDetected(DomainEvent):
    """Recorded in addition to `AIAnalysisCompleted` when a completed
    `MISINFORMATION` analysis carries `risk_level` `HIGH`/`CRITICAL` — the
    seam a future notification/moderation-queue subscriber would listen
    on. Never itself removes, restricts, or reports content — see
    `entities.py`'s own module docstring for why this module makes no
    write call into `community_moderation` at all."""

    analysis_id: UUID
    target_type: CommunityContentTargetType
    target_id: UUID
    risk_level: MisinformationRiskLevel
