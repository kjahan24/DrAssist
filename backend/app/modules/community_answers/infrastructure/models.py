"""SQLAlchemy ORM models for the Community Answers module.

Three tables: `community_answers` (many-to-one with `community_questions`,
`communities`, `organizations`, and `medical_topics` via its denormalized
`topic_id` — all cross-module FKs at the DB level, the same "one
physical database, real FK, decoupled application layers" pattern
`app.modules.community_questions.infrastructure.models
.CommunityQuestionModel` already establishes), `community_answer_revisions`
(many-to-one with `community_answers`; append-only, immutable — see
`CommunityAnswerRevisionRepository`'s own docstring), and
`community_answer_attachments` (many-to-one with both `community_answers`
and `medical_documents`).

`CommunityAnswerModel` carries no `SoftDeleteMixin` — like
`CommunityQuestionModel`, deletion is the business-visible `status ==
DELETED` value itself (see `AnswerStatus`'s own docstring), so there is
no separate `deleted_at` column.

A partial unique index (`uq_community_answers_question_id_best`, `WHERE
is_best_answer`) enforces "a question can have only one best answer" as
a DB-level safety net under concurrent requests, on top of the
application-level coordination `MarkBestAnswerService` already performs
— see that service's own docstring.

`community_answer_revisions` carries only `CreatedAtMixin`
(`created_at`, no `updated_at`) — the same shape
`CommunityQuestionTopicModel`/etc. already establish for their own
append-only child rows, here doubling as the literal enforcement of
"revision history must be immutable" (no ORM-level `onupdate`, and
`CommunityAnswerRevisionRepository` exposes no update/remove method at
all to even attempt a mutation through).

Indexes explicitly named by this task's own DATABASE section:
`question_id`, `author_id`, `status`, `created_at`, `published_at`,
`is_best_answer`, `is_featured`, `is_pinned` — plus composite indexes on
`(question_id|author_id|community_id|topic_id, status, published_at)`
serving `browse_feed()`'s own keyset-pagination query shape, mirroring
`CommunityQuestionModel`'s own composite-index precedent.
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
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility

_answer_status_enum = pg_enum(AnswerStatus, "answer_status_enum")
_answer_visibility_enum = pg_enum(AnswerVisibility, "answer_visibility_enum")


class CommunityAnswerModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_questions.id", ondelete="CASCADE"), nullable=False
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AnswerStatus] = mapped_column(
        _answer_status_enum, nullable=False, default=AnswerStatus.DRAFT
    )
    visibility: Mapped[AnswerVisibility] = mapped_column(
        _answer_visibility_enum, nullable=False, default=AnswerVisibility.PUBLIC
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_best_answer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    share_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_community_answers_question_id_best",
            "question_id",
            unique=True,
            postgresql_where=text("is_best_answer = true"),
        ),
        Index("ix_community_answers_question_id", "question_id"),
        Index("ix_community_answers_community_id", "community_id"),
        Index("ix_community_answers_organization_id", "organization_id"),
        Index("ix_community_answers_topic_id", "topic_id"),
        Index("ix_community_answers_author_id", "author_id"),
        Index("ix_community_answers_status", "status"),
        Index("ix_community_answers_created_at", "created_at"),
        Index("ix_community_answers_published_at", "published_at"),
        Index("ix_community_answers_is_best_answer", "is_best_answer"),
        Index("ix_community_answers_is_featured", "is_featured"),
        Index("ix_community_answers_is_pinned", "is_pinned"),
        Index(
            "ix_community_answers_question_id_status_published_at",
            "question_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_answers_author_id_status_published_at",
            "author_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_answers_community_id_status_published_at",
            "community_id",
            "status",
            "published_at",
        ),
        Index(
            "ix_community_answers_topic_id_status_published_at",
            "topic_id",
            "status",
            "published_at",
        ),
    )


class CommunityAnswerRevisionModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_answer_revisions"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_answers.id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_community_answer_revisions_answer_id", "answer_id"),
        Index(
            "ix_community_answer_revisions_answer_id_revision_number",
            "answer_id",
            "revision_number",
        ),
    )


class CommunityAnswerAttachmentModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_answer_attachments"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_answers.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "answer_id", "document_id", name="uq_community_answer_attachments_answer_id_document_id"
        ),
        Index("ix_community_answer_attachments_answer_id", "answer_id"),
        Index("ix_community_answer_attachments_document_id", "document_id"),
    )
