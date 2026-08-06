"""SQLAlchemy ORM models for the Community Posts module.

Four tables: `community_posts` (many-to-one with `communities` — the
Community module's own table, and `organizations`, both cross-module FKs
at the DB level, the same "one physical database, real FK, decoupled
application layers" pattern `medical_topics.created_by -> users.id`
already establishes for itself; optionally references `medical_documents`
for its featured image), `community_post_topics` (many-to-one with both
`community_posts` and `medical_topics`), `community_post_tags` (many-to-
one with `community_posts`, plain per-post free text — no separate tag-
vocabulary table, see `CommunityPostTag`'s own domain docstring),
`community_post_attachments` (many-to-one with both `community_posts`
and `medical_documents`).

`community_post_topics`/`community_post_tags`/`community_post_attachments`
carry only `CreatedAtMixin` (`created_at`, no `updated_at`) — none of
their domain entities has a single mutating method after `.create()`,
the same shape `medical_topic_aliases`/`medical_topic_relations` already
establish for themselves; each mapper synthesizes the domain aggregate's
required `updated_at` field as equal to `created_at`.

Three composite indexes (`(community_id, status, published_at)`/
`(organization_id, status, published_at)`/`(author_id, status,
published_at)`) exist specifically to serve `browse_feed()`'s own keyset-
pagination query shape (`WHERE <scope> AND status = 'published' ORDER BY
published_at DESC, id DESC`) — see `SqlAlchemyCommunityPostRepository
.browse_feed`'s own docstring.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility

_post_type_enum = pg_enum(PostType, "post_type_enum")
_post_status_enum = pg_enum(PostStatus, "post_status_enum")
_post_visibility_enum = pg_enum(PostVisibility, "post_visibility_enum")


class CommunityPostModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "community_posts"

    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    post_type: Mapped[PostType] = mapped_column(
        _post_type_enum, nullable=False, default=PostType.DISCUSSION
    )
    status: Mapped[PostStatus] = mapped_column(
        _post_status_enum, nullable=False, default=PostStatus.DRAFT
    )
    visibility: Mapped[PostVisibility] = mapped_column(
        _post_visibility_enum, nullable=False, default=PostVisibility.PUBLIC
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    featured_image_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("medical_documents.id", ondelete="SET NULL"), default=None
    )
    read_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bookmark_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    share_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_community_posts_community_id_slug",
            "community_id",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_community_posts_community_id", "community_id"),
        Index("ix_community_posts_organization_id", "organization_id"),
        Index("ix_community_posts_author_id", "author_id"),
        Index("ix_community_posts_status", "status"),
        Index("ix_community_posts_is_pinned", "is_pinned"),
        Index("ix_community_posts_is_featured", "is_featured"),
        Index("ix_community_posts_published_at", "published_at"),
        Index(
            "ix_community_posts_community_id_status_published_at",
            "community_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_posts_organization_id_status_published_at",
            "organization_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_posts_author_id_status_published_at",
            "author_id",
            "status",
            "published_at",
        ),
    )


class CommunityPostTopicModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_post_topics"

    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("post_id", "topic_id", name="uq_community_post_topics_post_id_topic_id"),
        Index("ix_community_post_topics_post_id", "post_id"),
        Index("ix_community_post_topics_topic_id", "topic_id"),
    )


class CommunityPostTagModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_post_tags"

    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("post_id", "tag", name="uq_community_post_tags_post_id_tag"),
        Index("ix_community_post_tags_post_id", "post_id"),
        Index("ix_community_post_tags_tag", "tag"),
    )


class CommunityPostAttachmentModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_post_attachments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "post_id", "document_id", name="uq_community_post_attachments_post_id_document_id"
        ),
        Index("ix_community_post_attachments_post_id", "post_id"),
        Index("ix_community_post_attachments_document_id", "document_id"),
    )
