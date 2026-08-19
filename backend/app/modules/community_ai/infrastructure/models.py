"""SQLAlchemy ORM model for the Community AI Features module.

One table: `community_ai_analyses` — matching this task's own PERSISTENCE
section ("Store AI analysis metadata: type, target, tenant, status,
result, confidence, model/provider used, timestamps").

`target_id` carries no foreign key, for the identical reason
`community_moderation`'s own `CommunityReportModel.target_id` has none
(see that module's own `models.py` docstring): one column cannot
conditionally reference `community_posts`/`community_questions`/
`community_answers`/`community_comments` at the schema level.
Existence/tenant/visibility validation happens once, at write time,
through each peer module's own public query port
(`_target_resolution.py`), never through a DB-level FK here.

`UniqueConstraint("target_type", "target_id", "analysis_type")` is what
makes `AICommunityAnalysis`'s own "one row per `(target_type, target_id,
analysis_type)`, mutated in place" domain rule (see `domain/entities.py`'s
own docstring) an enforced database invariant, not just an
application-level convention — the identical "unique constraint backs the
one-row-per-identity rule" precedent
`app.modules.community_engagement.infrastructure.models.VoteModel`'s own
`uq_votes_voter_target` already establishes.

`result` is `JSONB` — holds whichever of `CommunityDiscussionSummary`/
`tuple[SimilarDiscussion, ...]`/`tuple[TrustedResourceRecommendation,
...]`/`MisinformationAssessment` this row's `analysis_type` produced,
serialized by `application/services/_result_serialization.py`; this
table has no way to know or enforce which shape applies to a given row,
matching `_result_serialization.py`'s own docstring.
"""

import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)

_analysis_type_enum = pg_enum(AIAnalysisType, "ai_analysis_type_enum")
_target_type_enum = pg_enum(CommunityContentTargetType, "ai_community_content_target_type_enum")
_analysis_status_enum = pg_enum(AIAnalysisStatus, "ai_analysis_status_enum")


class CommunityAIAnalysisModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_ai_analyses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    analysis_type: Mapped[AIAnalysisType] = mapped_column(_analysis_type_enum, nullable=False)
    target_type: Mapped[CommunityContentTargetType] = mapped_column(
        _target_type_enum, nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[AIAnalysisStatus] = mapped_column(
        _analysis_status_enum, nullable=False, default=AIAnalysisStatus.PENDING
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=None)
    ai_provider: Mapped[str | None] = mapped_column(String(100), default=None)
    ai_model: Mapped[str | None] = mapped_column(String(200), default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)
    latency_ms: Mapped[float | None] = mapped_column(Float, default=None)

    __table_args__ = (
        UniqueConstraint(
            "target_type", "target_id", "analysis_type", name="uq_community_ai_analyses_target"
        ),
        Index("ix_community_ai_analyses_organization_id", "organization_id"),
        Index("ix_community_ai_analyses_target_type_target_id", "target_type", "target_id"),
        Index("ix_community_ai_analyses_status", "status"),
        Index("ix_community_ai_analyses_created_at", "created_at"),
    )


__all__ = ["CommunityAIAnalysisModel"]
