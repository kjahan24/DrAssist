"""create community posts tables

Phase 5.4 — Community Posts module: creates `community_posts` (the core
feed entity — many-to-one with `communities`/`organizations`, both
cross-module FKs at the DB level, the same "one physical database, real
FK, decoupled application layers" pattern
`bef8b3fd9a86_create_medical_topics_tables`'s own `medical_topics
.created_by -> users.id` already establishes; optionally references
`medical_documents` for its featured image), `community_post_topics`
(many-to-one with both `community_posts` and `medical_topics`, "Multiple
topics"), `community_post_tags` (many-to-one with `community_posts`,
plain per-post free text, "Multiple tags"), and `community_post_
attachments` (many-to-one with both `community_posts` and
`medical_documents`, "Attachment references" — "Reuse the existing File
module. Do NOT build upload/storage.").

No existing table (from any prior phase) is altered by this migration —
four wholly new tables only.

Revision ID: f76a3d107b67
Revises: bef8b3fd9a86
Create Date: 2026-08-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f76a3d107b67"
down_revision: str | None = "bef8b3fd9a86"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    post_type_enum = postgresql.ENUM(
        "discussion",
        "experience",
        "clinical_case",
        "medical_news",
        "research",
        "educational",
        "clinical_pearl",
        "announcement",
        name="post_type_enum",
        create_type=False,
    )
    post_type_enum.create(op.get_bind(), checkfirst=True)

    post_status_enum = postgresql.ENUM(
        "draft", "published", "archived", name="post_status_enum", create_type=False
    )
    post_status_enum.create(op.get_bind(), checkfirst=True)

    post_visibility_enum = postgresql.ENUM(
        "public", "members_only", "private", name="post_visibility_enum", create_type=False
    )
    post_visibility_enum.create(op.get_bind(), checkfirst=True)

    # --- community_posts ----------------------------------------------------------
    op.create_table(
        "community_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("post_type", post_type_enum, nullable=False, server_default="discussion"),
        sa.Column("status", post_status_enum, nullable=False, server_default="draft"),
        sa.Column("visibility", post_visibility_enum, nullable=False, server_default="public"),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("featured_image_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("read_time_minutes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmark_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("deleted_at", _TIMESTAMPTZ, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_community_posts"),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_posts_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_community_posts_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_community_posts_author_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_community_posts_updated_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["featured_image_document_id"],
            ["medical_documents.id"],
            name="fk_community_posts_featured_image_document_id_medical_documents",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "uq_community_posts_community_id_slug",
        "community_posts",
        ["community_id", "slug"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_community_posts_community_id", "community_posts", ["community_id"])
    op.create_index("ix_community_posts_organization_id", "community_posts", ["organization_id"])
    op.create_index("ix_community_posts_author_id", "community_posts", ["author_id"])
    op.create_index("ix_community_posts_status", "community_posts", ["status"])
    op.create_index("ix_community_posts_is_pinned", "community_posts", ["is_pinned"])
    op.create_index("ix_community_posts_is_featured", "community_posts", ["is_featured"])
    op.create_index("ix_community_posts_published_at", "community_posts", ["published_at"])
    op.create_index(
        "ix_community_posts_community_id_status_published_at",
        "community_posts",
        ["community_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_posts_organization_id_status_published_at",
        "community_posts",
        ["organization_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_posts_author_id_status_published_at",
        "community_posts",
        ["author_id", "status", "published_at"],
    )

    # --- community_post_topics ---------------------------------------------------
    op.create_table(
        "community_post_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_post_topics"),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            name="fk_community_post_topics_post_id_community_posts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_community_post_topics_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "post_id", "topic_id", name="uq_community_post_topics_post_id_topic_id"
        ),
    )
    op.create_index("ix_community_post_topics_post_id", "community_post_topics", ["post_id"])
    op.create_index("ix_community_post_topics_topic_id", "community_post_topics", ["topic_id"])

    # --- community_post_tags -----------------------------------------------------
    op.create_table(
        "community_post_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_post_tags"),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            name="fk_community_post_tags_post_id_community_posts",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("post_id", "tag", name="uq_community_post_tags_post_id_tag"),
    )
    op.create_index("ix_community_post_tags_post_id", "community_post_tags", ["post_id"])
    op.create_index("ix_community_post_tags_tag", "community_post_tags", ["tag"])

    # --- community_post_attachments -----------------------------------------------
    op.create_table(
        "community_post_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_post_attachments"),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            name="fk_community_post_attachments_post_id_community_posts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["medical_documents.id"],
            name="fk_community_post_attachments_document_id_medical_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "post_id", "document_id", name="uq_community_post_attachments_post_id_document_id"
        ),
    )
    op.create_index(
        "ix_community_post_attachments_post_id", "community_post_attachments", ["post_id"]
    )
    op.create_index(
        "ix_community_post_attachments_document_id", "community_post_attachments", ["document_id"]
    )


def downgrade() -> None:
    op.drop_table("community_post_attachments")
    op.drop_table("community_post_tags")
    op.drop_table("community_post_topics")
    op.drop_table("community_posts")

    postgresql.ENUM(name="post_visibility_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="post_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="post_type_enum").drop(op.get_bind(), checkfirst=True)
