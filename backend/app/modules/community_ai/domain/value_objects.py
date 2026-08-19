"""Domain value objects for the Community AI Features module.

`CommunityDiscussionSummary`, `TrustedResourceRecommendation`, and
`MisinformationAssessment` are the structured shape each corresponding
`AIAnalysisType` produces — `AICommunityAnalysis.result` stores one of
these (or a tuple of `SimilarDiscussion`/`TrustedResourceRecommendation`)
serialized to a JSONB dict by `infrastructure/mappers.py`; this file has
no knowledge of JSON or the database, per this codebase's own layering
rule.

`SimilarDiscussion` deliberately carries no title/excerpt/body — only
`target_type`/`target_id`/`similarity_score` — satisfying this task's own
"Avoid storing unnecessary raw conversation/content copies" SAFETY rule:
a caller resolves the target's current title/excerpt live, through
`PostQueryPort`/`QuestionQueryPort`/etc., at read time, the same "public
port is the single source of truth, never a cached copy" precedent
`community_moderation`'s own `ModerationAction.previous_state`/
`.new_state` (plain strings, never a duplicated content snapshot)
already establishes.

`TrustedMedicalSource` is not one of this task's own five named domain
types — it is the catalog entry `TrustedResourceCatalogPort` returns (see
`application/ports.py`), the mechanism that makes "Do NOT fabricate
medical sources" structural rather than a prompt instruction the model
could ignore: the AI ranks/selects from a known, curated set of real
organizations, it never invents a URL from scratch.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_ai.domain.enums import (
    CommunityContentTargetType,
    MisinformationRiskLevel,
    ResourceType,
)


@dataclass(frozen=True, slots=True)
class CommunityDiscussionSummary:
    key_points: tuple[str, ...]
    main_claims: tuple[str, ...]
    areas_of_agreement: tuple[str, ...]
    areas_of_disagreement: tuple[str, ...]
    unanswered_questions: tuple[str, ...]
    safety_disclaimer: str | None = None


@dataclass(frozen=True, slots=True)
class SimilarDiscussion:
    target_type: CommunityContentTargetType
    target_id: UUID
    similarity_score: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError("similarity_score must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class TrustedMedicalSource:
    title: str
    url: str
    resource_type: ResourceType
    topic_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TrustedResourceRecommendation:
    source_title: str
    source_url: str
    resource_type: ResourceType
    relevance_explanation: str
    confidence_score: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class MisinformationAssessment:
    risk_level: MisinformationRiskLevel
    claims: tuple[str, ...]
    evidence_needed: bool
    explanation: str
    confidence_score: float
    recommended_for_moderation_review: bool
    reference_suggestions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
