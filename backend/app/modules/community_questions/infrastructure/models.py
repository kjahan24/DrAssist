"""SQLAlchemy ORM models for the Community Questions module.

Five tables: `community_questions` (many-to-one with `communities`,
`organizations`, and `medical_topics` via its mandatory `primary_topic_id`
— all cross-module FKs at the DB level, the same "one physical database,
real FK, decoupled application layers" pattern
`app.modules.community_posts.infrastructure.models.CommunityPostModel`
already establishes), `community_question_topics` (many-to-one with both
`community_questions` and `medical_topics` — *secondary* topics only, see
`CommunityQuestionTopic`'s own domain docstring), `community_question_tags`
(many-to-one with `community_questions`, plain per-question free text),
`community_question_attachments` (many-to-one with both
`community_questions` and `medical_documents`), `community_question_followers`
(many-to-one with both `community_questions` and `users`).

`CommunityQuestionModel` carries no `SoftDeleteMixin` — unlike
`CommunityPostModel`, deletion here is the business-visible `status ==
DELETED` value itself (see `QuestionStatus`'s own docstring), so there is
no separate `deleted_at` column; the unique `(community_id, slug)` index
below is accordingly partial on `status != 'deleted'` rather than
`deleted_at IS NULL`, letting a deleted question's slug be reused by a
new one — the same *spirit* of Posts' own partial-uniqueness trick,
adapted to this module's status-based deletion.

`community_question_topics`/`community_question_tags`/
`community_question_attachments`/`community_question_followers` all
carry only `CreatedAtMixin` (`created_at`, no `updated_at`) — none of
their domain entities has a single mutating method after `.create()`,
the same shape `CommunityPostTopicModel`/`CommunityPostTagModel`/
`CommunityPostAttachmentModel` already establish; each mapper
synthesizes the domain aggregate's required `updated_at` field as equal
to `created_at`.

Four composite indexes on `community_questions`
(`(community_id, status, published_at)`/`(organization_id, status,
published_at)`/`(author_id, status, published_at)`/`(primary_topic_id,
status, published_at)`) exist specifically to serve `browse_feed()`'s
own keyset-pagination query shape — see
`SqlAlchemyCommunityQuestionRepository.browse_feed`'s own docstring. The
fourth (`primary_topic_id`) has no analog in `CommunityPostModel`, since
posts have no equivalent "mandatory primary topic" concept.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)

_question_type_enum = pg_enum(QuestionType, "question_type_enum")
_question_status_enum = pg_enum(QuestionStatus, "question_status_enum")
_question_visibility_enum = pg_enum(QuestionVisibility, "question_visibility_enum")


class CommunityQuestionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_questions"

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
    primary_topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        _question_type_enum, nullable=False, default=QuestionType.GENERAL
    )
    status: Mapped[QuestionStatus] = mapped_column(
        _question_status_enum, nullable=False, default=QuestionStatus.DRAFT
    )
    visibility: Mapped[QuestionVisibility] = mapped_column(
        _question_visibility_enum, nullable=False, default=QuestionVisibility.PUBLIC
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepted_answer_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    read_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    follower_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bookmark_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    share_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_community_questions_community_id_slug",
            "community_id",
            "slug",
            unique=True,
            postgresql_where=text("status != 'deleted'"),
        ),
        Index("ix_community_questions_community_id", "community_id"),
        Index("ix_community_questions_organization_id", "organization_id"),
        Index("ix_community_questions_author_id", "author_id"),
        Index("ix_community_questions_primary_topic_id", "primary_topic_id"),
        Index("ix_community_questions_status", "status"),
        Index("ix_community_questions_is_pinned", "is_pinned"),
        Index("ix_community_questions_is_featured", "is_featured"),
        Index("ix_community_questions_published_at", "published_at"),
        Index(
            "ix_community_questions_community_id_status_published_at",
            "community_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_questions_organization_id_status_published_at",
            "organization_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_questions_author_id_status_published_at",
            "author_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_questions_primary_topic_id_status_published_at",
            "primary_topic_id",
            "status",
            "published_at",
        ),
    )


class CommunityQuestionTopicModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_question_topics"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "community_questions.id",
            ondelete="CASCADE",
            name="fk_community_question_topics_question_id_questions",
        ),
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "question_id", "topic_id", name="uq_community_question_topics_question_id_topic_id"
        ),
        Index("ix_community_question_topics_question_id", "question_id"),
        Index("ix_community_question_topics_topic_id", "topic_id"),
    )


class CommunityQuestionTagModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_question_tags"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "community_questions.id",
            ondelete="CASCADE",
            name="fk_community_question_tags_question_id_questions",
        ),
        nullable=False,
    )
    tag: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("question_id", "tag", name="uq_community_question_tags_question_id_tag"),
        Index("ix_community_question_tags_question_id", "question_id"),
        Index("ix_community_question_tags_tag", "tag"),
    )


class CommunityQuestionAttachmentModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_question_attachments"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "community_questions.id",
            ondelete="CASCADE",
            name="fk_community_question_attachments_question_id_questions",
        ),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "question_id",
            "document_id",
            name="uq_community_question_attachments_question_id_document_id",
        ),
        Index("ix_community_question_attachments_question_id", "question_id"),
        Index("ix_community_question_attachments_document_id", "document_id"),
    )


class CommunityQuestionFollowerModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_question_followers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "community_questions.id",
            ondelete="CASCADE",
            name="fk_community_question_followers_question_id_questions",
        ),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "question_id", "user_id", name="uq_community_question_followers_question_id_user_id"
        ),
        Index("ix_community_question_followers_question_id", "question_id"),
        Index("ix_community_question_followers_user_id", "user_id"),
    )
