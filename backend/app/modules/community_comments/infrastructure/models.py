"""SQLAlchemy ORM models for the Community Comments module.

Three tables: `community_comments` (self-referential via
`parent_comment_id`/`root_comment_id` — see `CommunityComment`'s own
module docstring for the full "a reply is a `CommunityComment` row like
any other" reasoning; `target_id` has deliberately no foreign key — a
single column cannot reference `community_posts`/`community_questions`/
`community_answers` conditionally at the schema level, so existence is
validated once, at write time, through each peer module's own public
query port instead, see `_target_resolution.py`'s own docstring),
`community_comment_revisions` (many-to-one with `community_comments`;
append-only and immutable — see `CommunityCommentRevisionRepository`'s
own docstring), and `community_comment_attachments` (many-to-one with
both `community_comments` and `medical_documents`).

`CommunityCommentModel` carries no `SoftDeleteMixin` — like
`CommunityAnswerModel`, deletion is the business-visible `status ==
DELETED` value itself (see `CommentStatus`'s own docstring), so there is
no separate `deleted_at` column.

`root_comment_id`/`depth` are the pair that lets a whole bounded-depth
conversation be fetched with one flat `WHERE root_comment_id = X AND
depth <= N` query, never a recursive CTE — see `CommunityCommentRepository
.get_thread`'s own docstring.

Indexes explicitly named by this task's own DATABASE section: "target
identifiers" (`target_type`+`target_id`), `parent_comment_id`,
`author_id`, `community_id`, `status`, `created_at`, `published_at` —
plus `(root_comment_id, depth)` serving `get_thread()`, and composite
`(target_type, target_id, status, created_at)`/`(parent_comment_id,
status, created_at)` serving `browse()`'s own keyset-pagination query
shapes for `ListCommentsService`/`ListRepliesService`, mirroring
`CommunityAnswerModel`'s own composite-index precedent.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType

_comment_status_enum = pg_enum(CommentStatus, "comment_status_enum")
_comment_target_type_enum = pg_enum(CommentTargetType, "comment_target_type_enum")


class CommunityCommentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_comments"

    target_type: Mapped[CommentTargetType] = mapped_column(
        _comment_target_type_enum, nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), default=None
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_comments.id", ondelete="CASCADE"), default=None
    )
    root_comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=False
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[CommentStatus] = mapped_column(
        _comment_status_enum, nullable=False, default=CommentStatus.DRAFT
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index("ix_community_comments_target_type_target_id", "target_type", "target_id"),
        Index("ix_community_comments_parent_comment_id", "parent_comment_id"),
        Index("ix_community_comments_root_comment_id_depth", "root_comment_id", "depth"),
        Index("ix_community_comments_author_id", "author_id"),
        Index("ix_community_comments_community_id", "community_id"),
        Index("ix_community_comments_organization_id", "organization_id"),
        Index("ix_community_comments_topic_id", "topic_id"),
        Index("ix_community_comments_status", "status"),
        Index("ix_community_comments_created_at", "created_at"),
        Index("ix_community_comments_published_at", "published_at"),
        Index(
            "ix_community_comments_target_status_created",
            "target_type",
            "target_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_community_comments_parent_status_created",
            "parent_comment_id",
            "status",
            "created_at",
        ),
    )


class CommunityCommentRevisionModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_comment_revisions"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_community_comment_revisions_comment_id", "comment_id"),
        Index(
            "ix_community_comment_revisions_comment_id_revision_number",
            "comment_id",
            "revision_number",
        ),
    )


class CommunityCommentAttachmentModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_comment_attachments"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "comment_id",
            "document_id",
            name="uq_community_comment_attachments_comment_id_document_id",
        ),
        Index("ix_community_comment_attachments_comment_id", "comment_id"),
        Index("ix_community_comment_attachments_document_id", "document_id"),
    )
