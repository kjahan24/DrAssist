"""create community questions tables

Phase 5.5 — Community Questions module: creates `community_questions`
(the core Quora-style Q&A entity — many-to-one with `communities`/
`organizations`/`medical_topics` via its mandatory `primary_topic_id`, all
cross-module FKs at the DB level, the same "one physical database, real
FK, decoupled application layers" pattern
`f76a3d107b67_create_community_posts_tables`'s own `community_posts
.community_id -> communities.id` already establishes), `community_question
_topics` (many-to-one with both `community_questions` and `medical_topics`
— *secondary* topics only, "Multiple topics"), `community_question_tags`
(many-to-one with `community_questions`, plain per-question free text,
"Question Tags"), `community_question_attachments` (many-to-one with both
`community_questions` and `medical_documents`, "Attachment references" —
"Reuse existing File module"), and `community_question_followers`
(many-to-one with both `community_questions` and `users`, "Follower
Count").

`community_questions` has no `deleted_at` column — deletion is the
business-visible `status == 'deleted'` value itself (`question_status_enum`
has five members: draft/published/closed/archived/deleted), unlike
`community_posts`' own infrastructure-only soft delete; the unique
`(community_id, slug)` index is accordingly partial on
`status != 'deleted'` rather than `deleted_at IS NULL`.

No existing table (from any prior phase) is altered by this migration —
five wholly new tables only.

Revision ID: a5782d644279
Revises: f76a3d107b67
Create Date: 2026-08-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a5782d644279"
down_revision: str | None = "f76a3d107b67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    question_type_enum = postgresql.ENUM(
        "general",
        "clinical",
        "patient_experience",
        "treatment_advice",
        "medication_question",
        "diagnosis_discussion",
        "research_question",
        "educational_question",
        name="question_type_enum",
        create_type=False,
    )
    question_type_enum.create(op.get_bind(), checkfirst=True)

    question_status_enum = postgresql.ENUM(
        "draft",
        "published",
        "closed",
        "archived",
        "deleted",
        name="question_status_enum",
        create_type=False,
    )
    question_status_enum.create(op.get_bind(), checkfirst=True)

    question_visibility_enum = postgresql.ENUM(
        "public", "members_only", "private", name="question_visibility_enum", create_type=False
    )
    question_visibility_enum.create(op.get_bind(), checkfirst=True)

    # --- community_questions --------------------------------------------------
    op.create_table(
        "community_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("question_type", question_type_enum, nullable=False, server_default="general"),
        sa.Column("status", question_status_enum, nullable=False, server_default="draft"),
        sa.Column("visibility", question_visibility_enum, nullable=False, server_default="public"),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("accepted_answer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("read_time_minutes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("follower_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmark_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_community_questions"),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_questions_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_community_questions_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_community_questions_author_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_community_questions_updated_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["primary_topic_id"],
            ["medical_topics.id"],
            name="fk_community_questions_primary_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "uq_community_questions_community_id_slug",
        "community_questions",
        ["community_id", "slug"],
        unique=True,
        postgresql_where=sa.text("status != 'deleted'"),
    )
    op.create_index("ix_community_questions_community_id", "community_questions", ["community_id"])
    op.create_index(
        "ix_community_questions_organization_id", "community_questions", ["organization_id"]
    )
    op.create_index("ix_community_questions_author_id", "community_questions", ["author_id"])
    op.create_index(
        "ix_community_questions_primary_topic_id", "community_questions", ["primary_topic_id"]
    )
    op.create_index("ix_community_questions_status", "community_questions", ["status"])
    op.create_index("ix_community_questions_is_pinned", "community_questions", ["is_pinned"])
    op.create_index("ix_community_questions_is_featured", "community_questions", ["is_featured"])
    op.create_index("ix_community_questions_published_at", "community_questions", ["published_at"])
    op.create_index(
        "ix_community_questions_community_id_status_published_at",
        "community_questions",
        ["community_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_questions_organization_id_status_published_at",
        "community_questions",
        ["organization_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_questions_author_id_status_published_at",
        "community_questions",
        ["author_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_questions_primary_topic_id_status_published_at",
        "community_questions",
        ["primary_topic_id", "status", "published_at"],
    )

    # --- community_question_topics ---------------------------------------------
    op.create_table(
        "community_question_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_question_topics"),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["community_questions.id"],
            name="fk_community_question_topics_question_id_questions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_community_question_topics_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "question_id",
            "topic_id",
            name="uq_community_question_topics_question_id_topic_id",
        ),
    )
    op.create_index(
        "ix_community_question_topics_question_id", "community_question_topics", ["question_id"]
    )
    op.create_index(
        "ix_community_question_topics_topic_id", "community_question_topics", ["topic_id"]
    )

    # --- community_question_tags -------------------------------------------------
    op.create_table(
        "community_question_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_question_tags"),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["community_questions.id"],
            name="fk_community_question_tags_question_id_questions",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "question_id", "tag", name="uq_community_question_tags_question_id_tag"
        ),
    )
    op.create_index(
        "ix_community_question_tags_question_id", "community_question_tags", ["question_id"]
    )
    op.create_index("ix_community_question_tags_tag", "community_question_tags", ["tag"])

    # --- community_question_attachments -------------------------------------------
    op.create_table(
        "community_question_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_question_attachments"),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["community_questions.id"],
            name="fk_community_question_attachments_question_id_questions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["medical_documents.id"],
            name="fk_community_question_attachments_document_id_medical_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "question_id",
            "document_id",
            name="uq_community_question_attachments_question_id_document_id",
        ),
    )
    op.create_index(
        "ix_community_question_attachments_question_id",
        "community_question_attachments",
        ["question_id"],
    )
    op.create_index(
        "ix_community_question_attachments_document_id",
        "community_question_attachments",
        ["document_id"],
    )

    # --- community_question_followers -----------------------------------------------
    op.create_table(
        "community_question_followers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_question_followers"),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["community_questions.id"],
            name="fk_community_question_followers_question_id_questions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_community_question_followers_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "question_id",
            "user_id",
            name="uq_community_question_followers_question_id_user_id",
        ),
    )
    op.create_index(
        "ix_community_question_followers_question_id",
        "community_question_followers",
        ["question_id"],
    )
    op.create_index(
        "ix_community_question_followers_user_id", "community_question_followers", ["user_id"]
    )


def downgrade() -> None:
    op.drop_table("community_question_followers")
    op.drop_table("community_question_attachments")
    op.drop_table("community_question_tags")
    op.drop_table("community_question_topics")
    op.drop_table("community_questions")

    postgresql.ENUM(name="question_visibility_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="question_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="question_type_enum").drop(op.get_bind(), checkfirst=True)
