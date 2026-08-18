"""create community comments tables

Phase 5.7 — Comments & Replies module: creates `community_comments` (a
single, self-referential table backing both top-level comments and
nested replies at any depth — see `CommunityComment`'s own module
docstring for the full "a reply is a `CommunityComment` row like any
other" reasoning; attaches to `community_posts`/`community_questions`/
`community_answers` via `target_type`+`target_id`, deliberately with no
foreign key on `target_id` itself — a single column cannot reference
three different tables conditionally at the schema level, so existence
is validated once, at write time, through each peer module's own public
query port instead), `community_comment_revisions` (many-to-one with
`community_comments`, append-only and immutable — "Comment Revision
History"), and `community_comment_attachments` (many-to-one with both
`community_comments` and `medical_documents`, "Comment Attachments" —
"Reuse the existing file/document storage architecture").

`community_comments` has no `deleted_at` column — deletion is the
business-visible `status == 'deleted'` value itself (`comment_status_enum`
has four members: draft/published/archived/deleted), the same
status-based deletion `community_answers` already establishes for itself.

`parent_comment_id`/`root_comment_id` are both self-referential foreign
keys onto `community_comments.id` itself — `root_comment_id` is NOT NULL
and, for a top-level comment, equals that same row's own `id` (a single
INSERT statement setting both is valid; PostgreSQL validates a
self-referencing foreign key against the fully-constructed row, not
incrementally). Together with `depth`, this lets an entire bounded-depth
conversation be fetched with one flat, indexed `WHERE root_comment_id = X
AND depth <= N` query — never a recursive CTE, satisfying this task's own
"Do not use unbounded recursive queries" / "Use safe bounded-depth thread
retrieval" instructions.

No existing table (from any prior phase) is altered by this migration —
three wholly new tables only.

Revision ID: d2627788d3c5
Revises: 1dc1fd199d41
Create Date: 2026-08-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2627788d3c5"
down_revision: str | None = "1dc1fd199d41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    comment_status_enum = postgresql.ENUM(
        "draft",
        "published",
        "archived",
        "deleted",
        name="comment_status_enum",
        create_type=False,
    )
    comment_status_enum.create(op.get_bind(), checkfirst=True)

    comment_target_type_enum = postgresql.ENUM(
        "post", "question", "answer", name="comment_target_type_enum", create_type=False
    )
    comment_target_type_enum.create(op.get_bind(), checkfirst=True)

    # --- community_comments -----------------------------------------------------
    op.create_table(
        "community_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", comment_target_type_enum, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("parent_comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("root_comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", comment_status_enum, nullable=False, server_default="draft"),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_community_comments"),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_comments_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_community_comments_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_community_comments_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_community_comments_author_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_community_comments_updated_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_comment_id"],
            ["community_comments.id"],
            name="fk_community_comments_parent_comment_id_community_comments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["root_comment_id"],
            ["community_comments.id"],
            name="fk_community_comments_root_comment_id_community_comments",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_community_comments_target_type_target_id",
        "community_comments",
        ["target_type", "target_id"],
    )
    op.create_index(
        "ix_community_comments_parent_comment_id", "community_comments", ["parent_comment_id"]
    )
    op.create_index(
        "ix_community_comments_root_comment_id_depth",
        "community_comments",
        ["root_comment_id", "depth"],
    )
    op.create_index("ix_community_comments_author_id", "community_comments", ["author_id"])
    op.create_index("ix_community_comments_community_id", "community_comments", ["community_id"])
    op.create_index(
        "ix_community_comments_organization_id", "community_comments", ["organization_id"]
    )
    op.create_index("ix_community_comments_topic_id", "community_comments", ["topic_id"])
    op.create_index("ix_community_comments_status", "community_comments", ["status"])
    op.create_index("ix_community_comments_created_at", "community_comments", ["created_at"])
    op.create_index("ix_community_comments_published_at", "community_comments", ["published_at"])
    op.create_index(
        "ix_community_comments_target_status_created",
        "community_comments",
        ["target_type", "target_id", "status", "created_at"],
    )
    op.create_index(
        "ix_community_comments_parent_status_created",
        "community_comments",
        ["parent_comment_id", "status", "created_at"],
    )

    # --- community_comment_revisions ---------------------------------------------
    op.create_table(
        "community_comment_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_body", sa.Text(), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_comment_revisions"),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["community_comments.id"],
            name="fk_community_comment_revisions_comment_id_community_comments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name="fk_community_comment_revisions_author_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_community_comment_revisions_comment_id", "community_comment_revisions", ["comment_id"]
    )
    op.create_index(
        "ix_community_comment_revisions_comment_id_revision_number",
        "community_comment_revisions",
        ["comment_id", "revision_number"],
    )

    # --- community_comment_attachments -----------------------------------------------
    op.create_table(
        "community_comment_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_comment_attachments"),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["community_comments.id"],
            name="fk_community_comment_attachments_comment_id_community_comments",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["medical_documents.id"],
            name="fk_community_comment_attachments_document_id_medical_documents",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "comment_id",
            "document_id",
            name="uq_community_comment_attachments_comment_id_document_id",
        ),
    )
    op.create_index(
        "ix_community_comment_attachments_comment_id",
        "community_comment_attachments",
        ["comment_id"],
    )
    op.create_index(
        "ix_community_comment_attachments_document_id",
        "community_comment_attachments",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_table("community_comment_attachments")
    op.drop_table("community_comment_revisions")
    op.drop_table("community_comments")

    postgresql.ENUM(name="comment_target_type_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="comment_status_enum").drop(op.get_bind(), checkfirst=True)
