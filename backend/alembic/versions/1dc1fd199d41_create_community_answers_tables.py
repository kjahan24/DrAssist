"""create community answers tables

Phase 5.6 — Community Answers module: creates `community_answers` (the
core Quora-style answer entity — many-to-one with `community_questions`,
`communities`, `organizations`, and `medical_topics` via its denormalized
`topic_id`, all cross-module FKs at the DB level, the same "one physical
database, real FK, decoupled application layers" pattern
`a5782d644279_create_community_questions_tables`'s own `community_questions
.primary_topic_id -> medical_topics.id` already establishes),
`community_answer_revisions` (many-to-one with `community_answers`,
append-only and immutable — "Answer Revision History"), and
`community_answer_attachments` (many-to-one with both `community_answers`
and `medical_documents`, "Answer Attachments" — "Reuse the existing
File/Document storage architecture").

`community_answers` has no `deleted_at` column — deletion is the
business-visible `status == 'deleted'` value itself
(`answer_status_enum` has four members: draft/published/archived/deleted),
the same status-based deletion `community_questions` already establishes
for itself.

A partial unique index (`uq_community_answers_question_id_best`, `WHERE
is_best_answer = true`) enforces "a question can have only one best
answer" as a DB-level safety net under concurrent requests.

No existing table (from any prior phase) is altered by this migration —
three wholly new tables only.

Revision ID: 1dc1fd199d41
Revises: a5782d644279
Create Date: 2026-08-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1dc1fd199d41"
down_revision: str | None = "a5782d644279"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    answer_status_enum = postgresql.ENUM(
        "draft",
        "published",
        "archived",
        "deleted",
        name="answer_status_enum",
        create_type=False,
    )
    answer_status_enum.create(op.get_bind(), checkfirst=True)

    answer_visibility_enum = postgresql.ENUM(
        "public", "members_only", "private", name="answer_visibility_enum", create_type=False
    )
    answer_visibility_enum.create(op.get_bind(), checkfirst=True)

    # --- community_answers -----------------------------------------------------
    op.create_table(
        "community_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", answer_status_enum, nullable=False, server_default="draft"),
        sa.Column("visibility", answer_visibility_enum, nullable=False, server_default="public"),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_best_answer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_community_answers"),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["community_questions.id"],
            name="fk_community_answers_question_id_community_questions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_answers_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_community_answers_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_community_answers_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_community_answers_author_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_community_answers_updated_by_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "uq_community_answers_question_id_best",
        "community_answers",
        ["question_id"],
        unique=True,
        postgresql_where=sa.text("is_best_answer = true"),
    )
    op.create_index("ix_community_answers_question_id", "community_answers", ["question_id"])
    op.create_index("ix_community_answers_community_id", "community_answers", ["community_id"])
    op.create_index(
        "ix_community_answers_organization_id", "community_answers", ["organization_id"]
    )
    op.create_index("ix_community_answers_topic_id", "community_answers", ["topic_id"])
    op.create_index("ix_community_answers_author_id", "community_answers", ["author_id"])
    op.create_index("ix_community_answers_status", "community_answers", ["status"])
    op.create_index("ix_community_answers_created_at", "community_answers", ["created_at"])
    op.create_index("ix_community_answers_published_at", "community_answers", ["published_at"])
    op.create_index("ix_community_answers_is_best_answer", "community_answers", ["is_best_answer"])
    op.create_index("ix_community_answers_is_featured", "community_answers", ["is_featured"])
    op.create_index("ix_community_answers_is_pinned", "community_answers", ["is_pinned"])
    op.create_index(
        "ix_community_answers_question_id_status_published_at",
        "community_answers",
        ["question_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_answers_author_id_status_published_at",
        "community_answers",
        ["author_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_answers_community_id_status_published_at",
        "community_answers",
        ["community_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_answers_topic_id_status_published_at",
        "community_answers",
        ["topic_id", "status", "published_at"],
    )

    # --- community_answer_revisions ---------------------------------------------
    op.create_table(
        "community_answer_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_body", sa.Text(), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_answer_revisions"),
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["community_answers.id"],
            name="fk_community_answer_revisions_answer_id_community_answers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_community_answer_revisions_author_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_community_answer_revisions_answer_id", "community_answer_revisions", ["answer_id"]
    )
    op.create_index(
        "ix_community_answer_revisions_answer_id_revision_number",
        "community_answer_revisions",
        ["answer_id", "revision_number"],
    )

    # --- community_answer_attachments -----------------------------------------------
    op.create_table(
        "community_answer_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_answer_attachments"),
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["community_answers.id"],
            name="fk_community_answer_attachments_answer_id_community_answers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["medical_documents.id"],
            name="fk_community_answer_attachments_document_id_medical_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "answer_id",
            "document_id",
            name="uq_community_answer_attachments_answer_id_document_id",
        ),
    )
    op.create_index(
        "ix_community_answer_attachments_answer_id",
        "community_answer_attachments",
        ["answer_id"],
    )
    op.create_index(
        "ix_community_answer_attachments_document_id",
        "community_answer_attachments",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_table("community_answer_attachments")
    op.drop_table("community_answer_revisions")
    op.drop_table("community_answers")

    postgresql.ENUM(name="answer_visibility_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="answer_status_enum").drop(op.get_bind(), checkfirst=True)
