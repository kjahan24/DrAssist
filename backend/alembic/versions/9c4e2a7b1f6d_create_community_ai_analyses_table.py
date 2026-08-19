"""create community ai analyses table

Phase 5.10 — AI Community Features module: creates one table —
`community_ai_analyses` — matching this task's own PERSISTENCE section
("Store AI analysis metadata: type, target, tenant, status, result,
confidence, model/provider used, timestamps").

`target_id` carries no foreign key, for the identical reason
`community_reports.target_id`/`moderation_actions.target_id` (migration
`7f3a19c6d8e2`) have none: a single column cannot conditionally reference
`community_posts`/`community_questions`/`community_answers`/
`community_comments` at the schema level; existence/tenant/visibility
validation happens once, at write time, through each peer module's own
public query port instead.

`uq_community_ai_analyses_target` on `(target_type, target_id,
analysis_type)` is what makes `AICommunityAnalysis`'s own "one row per
target+analysis-type, mutated in place" domain rule an enforced database
invariant, not just an application-level convention — see
`app/modules/community_ai/infrastructure/models.py`'s own docstring.

No existing table (from any prior phase) is altered by this migration —
one wholly new table only.

Revision ID: 9c4e2a7b1f6d
Revises: 7f3a19c6d8e2
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9c4e2a7b1f6d"
down_revision: str | None = "7f3a19c6d8e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    ai_analysis_type_enum = postgresql.ENUM(
        "summary",
        "similar_discussions",
        "resource_recommendation",
        "misinformation",
        name="ai_analysis_type_enum",
        create_type=False,
    )
    ai_analysis_type_enum.create(op.get_bind(), checkfirst=True)

    ai_community_content_target_type_enum = postgresql.ENUM(
        "post",
        "question",
        "answer",
        "comment",
        name="ai_community_content_target_type_enum",
        create_type=False,
    )
    ai_community_content_target_type_enum.create(op.get_bind(), checkfirst=True)

    ai_analysis_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="ai_analysis_status_enum",
        create_type=False,
    )
    ai_analysis_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "community_ai_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_type", ai_analysis_type_enum, nullable=False),
        sa.Column("target_type", ai_community_content_target_type_enum, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", ai_analysis_status_enum, nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("ai_provider", sa.String(length=100), nullable=True),
        sa.Column("ai_model", sa.String(length=200), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_community_ai_analyses"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_community_ai_analyses_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "target_type", "target_id", "analysis_type", name="uq_community_ai_analyses_target"
        ),
    )
    op.create_index(
        "ix_community_ai_analyses_organization_id", "community_ai_analyses", ["organization_id"]
    )
    op.create_index(
        "ix_community_ai_analyses_target_type_target_id",
        "community_ai_analyses",
        ["target_type", "target_id"],
    )
    op.create_index("ix_community_ai_analyses_status", "community_ai_analyses", ["status"])
    op.create_index(
        "ix_community_ai_analyses_created_at", "community_ai_analyses", ["created_at"]
    )


def downgrade() -> None:
    op.drop_table("community_ai_analyses")

    postgresql.ENUM(name="ai_analysis_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="ai_community_content_target_type_enum").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="ai_analysis_type_enum").drop(op.get_bind(), checkfirst=True)
