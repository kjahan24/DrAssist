"""Community Questions module aggregate roots: CommunityQuestion,
CommunityQuestionTopic, CommunityQuestionTag, CommunityQuestionFollower,
CommunityQuestionAttachment.

Each is its own aggregate — every reference to another aggregate,
including cross-module ones (`community_id` -> Community, `author_id`/
`updated_by`/`user_id` -> User, `primary_topic_id`/`topic_id` ->
MedicalTopic, `document_id` -> MedicalDocument), is by ID only, never by
object reference — the same rule `app.modules.community_posts.domain
.entities` already follows. Cross-module ID references are validated by
the application layer via that peer module's own public query port
(`CommunityQueryPort`/`TopicQueryPort`/`DocumentQueryPort`), never by
importing across `domain/` packages.

`CommunityQuestion.organization_id` is stored directly (denormalized from
the parent `Community` at creation time by `CreateQuestionService`), not
resolved via a `community_id` join on every query — the same "tenant id
stored directly on the tenant-scoped row" shape `CommunityPost
.organization_id` already establishes.

`accepted_answer_id` is a declared placeholder field only — this task's
own GOAL section states Answers are explicitly NOT part of this module
("Questions will later receive: Answers... but those are NOT part of
this module"), so there is no domain method to set it and no service
constructs one; a future Answers module populates it once it exists,
the same "declared but not yet actionable" shape `view_count`/
`bookmark_count`/`share_count` already establish for themselves (see
below).

`view_count`/`bookmark_count`/`share_count` are declared fields only —
this task's own APPLICATION section names no "record a view/bookmark/
share" use case, so nothing in this module increments them yet, matching
`CommunityPost`'s own identical reasoning. `follower_count` is different:
this task's own DOMAIN section names `CommunityQuestionFollower` as a
real entity (not just a counter), and `ManageQuestionFollowersService`
(this module's own "add what's genuinely required" service, mirroring
`app.modules.community_posts.application.services
.manage_post_topics_service`'s own precedent) actually creates/removes
follower rows — so `follower_count` *is* kept in sync, via
`increment_follower_count`/`decrement_follower_count`, called only by
that service.

`CommunityQuestionTopic`/`CommunityQuestionTag`/`CommunityQuestionAttachment`/
`CommunityQuestionFollower` all enforce no soft-delete: a row is either
present or absent, never edited — the same "hard delete, no historical
value" shape `CommunityPostTopic`/`CommunityPostTag`/
`CommunityPostAttachment` already establish for themselves.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.events import (
    CommunityQuestionArchived,
    CommunityQuestionAttachmentAdded,
    CommunityQuestionClosed,
    CommunityQuestionCreated,
    CommunityQuestionDeleted,
    CommunityQuestionFeaturedChanged,
    CommunityQuestionFollowed,
    CommunityQuestionPinnedChanged,
    CommunityQuestionPublished,
    CommunityQuestionReopened,
    CommunityQuestionTagAssigned,
    CommunityQuestionTopicAssigned,
    CommunityQuestionUnfollowed,
    CommunityQuestionUpdated,
)
from app.modules.community_questions.domain.exceptions import (
    QuestionAlreadyArchivedError,
    QuestionAlreadyClosedError,
    QuestionAlreadyDeletedError,
    QuestionAlreadyPublishedError,
    QuestionBodyRequiredError,
    QuestionNotClosedError,
    QuestionTagRequiredError,
    QuestionTagTooLongError,
)
from app.modules.community_questions.domain.value_objects import (
    QuestionId,
    QuestionSlug,
    QuestionSummary,
    QuestionTitle,
)
from app.shared.domain.entity import AggregateRoot

_WORDS_PER_MINUTE = 200
_TAG_MAX_LENGTH = 50


def _compute_read_time_minutes(body: str) -> int:
    word_count = len(body.split())
    return max(math.ceil(word_count / _WORDS_PER_MINUTE), 1)


@dataclass(kw_only=True, eq=False)
class CommunityQuestion(AggregateRoot):
    community_id: UUID
    organization_id: UUID
    author_id: UUID
    primary_topic_id: UUID
    slug: QuestionSlug
    title: QuestionTitle
    body: str
    summary: QuestionSummary
    question_type: QuestionType = QuestionType.GENERAL
    status: QuestionStatus = QuestionStatus.DRAFT
    visibility: QuestionVisibility = QuestionVisibility.PUBLIC
    is_anonymous: bool = False
    is_pinned: bool = False
    is_featured: bool = False
    accepted_answer_id: UUID | None = None
    read_time_minutes: int = 1
    view_count: int = 0
    follower_count: int = 0
    bookmark_count: int = 0
    share_count: int = 0
    published_at: datetime | None = None
    updated_by: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        community_id: UUID,
        organization_id: UUID,
        author_id: UUID,
        primary_topic_id: UUID,
        title: QuestionTitle,
        body: str,
        slug: QuestionSlug | None = None,
        summary: QuestionSummary | None = None,
        question_type: QuestionType = QuestionType.GENERAL,
        visibility: QuestionVisibility = QuestionVisibility.PUBLIC,
        is_anonymous: bool = False,
    ) -> "CommunityQuestion":
        if not body.strip():
            raise QuestionBodyRequiredError()

        question = cls(
            community_id=community_id,
            organization_id=organization_id,
            author_id=author_id,
            primary_topic_id=primary_topic_id,
            slug=slug if slug is not None else QuestionSlug.from_title(str(title)),
            title=title,
            body=body,
            summary=summary if summary is not None else QuestionSummary.from_body(body),
            question_type=question_type,
            visibility=visibility,
            is_anonymous=is_anonymous,
            read_time_minutes=_compute_read_time_minutes(body),
            updated_by=author_id,
        )
        question.record_event(
            CommunityQuestionCreated(
                question_id=question.id,
                community_id=community_id,
                author_id=author_id,
                slug=str(question.slug),
                title=str(title),
            )
        )
        return question

    def update_content(
        self,
        *,
        title: QuestionTitle | None = None,
        body: str | None = None,
        summary: QuestionSummary | None = None,
        regenerate_summary: bool = False,
        question_type: QuestionType | None = None,
        visibility: QuestionVisibility | None = None,
        is_anonymous: bool | None = None,
        updated_by: UUID | None = None,
    ) -> None:
        """`regenerate_summary=True` re-derives `summary` from the (new)
        `body` — otherwise, editing `body` deliberately leaves an
        existing, possibly hand-written `summary` untouched, the same
        behavior `CommunityPost.update_content` already establishes for
        its own `excerpt`."""
        if title is not None:
            self.title = title
        if body is not None:
            if not body.strip():
                raise QuestionBodyRequiredError()
            self.body = body
            self.read_time_minutes = _compute_read_time_minutes(body)
        if summary is not None:
            self.summary = summary
        elif regenerate_summary:
            self.summary = QuestionSummary.from_body(self.body)
        if question_type is not None:
            self.question_type = question_type
        if visibility is not None:
            self.visibility = visibility
        if is_anonymous is not None:
            self.is_anonymous = is_anonymous
        if updated_by is not None:
            self.updated_by = updated_by

        self.touch()
        self.record_event(CommunityQuestionUpdated(question_id=self.id))

    def publish(self) -> None:
        if self.status is QuestionStatus.PUBLISHED:
            raise QuestionAlreadyPublishedError(self.id)
        self.status = QuestionStatus.PUBLISHED
        self.published_at = datetime.now(UTC)
        self.touch()
        self.record_event(
            CommunityQuestionPublished(question_id=self.id, community_id=self.community_id)
        )

    def archive(self) -> None:
        if self.status is QuestionStatus.ARCHIVED:
            raise QuestionAlreadyArchivedError(self.id)
        self.status = QuestionStatus.ARCHIVED
        self.touch()
        self.record_event(CommunityQuestionArchived(question_id=self.id))

    def close(self) -> None:
        """Closes the question to further engagement — see
        `QuestionStatus`'s own docstring for why this is a dedicated
        PUBLISHED<->CLOSED toggle, distinct from `publish()`/`archive()`.
        Permissive from any non-CLOSED status (mirrors `publish()`/
        `archive()`'s own "just guard against the already-in-that-state
        case" permissiveness) — a draft or archived question can be
        closed directly, matching the identical flexibility
        `CommunityPost.archive` already allows for DRAFT->ARCHIVED."""
        if self.status is QuestionStatus.CLOSED:
            raise QuestionAlreadyClosedError(self.id)
        self.status = QuestionStatus.CLOSED
        self.touch()
        self.record_event(CommunityQuestionClosed(question_id=self.id))

    def reopen(self) -> None:
        """The inverse of `close()` — unlike every other transition on
        this aggregate, `reopen()` is deliberately *not* permissive: "re"
        opening only makes sense starting from CLOSED, so this is the one
        method here that requires a specific prior status rather than
        merely rejecting the same-state case."""
        if self.status is not QuestionStatus.CLOSED:
            raise QuestionNotClosedError(self.id)
        self.status = QuestionStatus.PUBLISHED
        self.touch()
        self.record_event(CommunityQuestionReopened(question_id=self.id))

    def delete(self) -> None:
        """Business-visible soft delete via status transition — see
        `QuestionStatus`'s own docstring for why this differs from
        `CommunityPost`'s purely-infrastructure-level deletion."""
        if self.status is QuestionStatus.DELETED:
            raise QuestionAlreadyDeletedError(self.id)
        self.status = QuestionStatus.DELETED
        self.touch()
        self.record_event(CommunityQuestionDeleted(question_id=self.id))

    def set_pinned(self, value: bool) -> None:
        """Community-moderator-only action — the same
        `CommunityPost.set_pinned` shape, scoped to how a question sorts
        within its *own* community's feed."""
        if self.is_pinned is value:
            return
        self.is_pinned = value
        self.touch()
        self.record_event(CommunityQuestionPinnedChanged(question_id=self.id, is_pinned=value))

    def set_featured(self, value: bool) -> None:
        """Platform/community-level curation flag — the same
        `set_featured` shape `CommunityPost`/`Community`/`MedicalTopic`
        already establish for themselves."""
        if self.is_featured is value:
            return
        self.is_featured = value
        self.touch()
        self.record_event(CommunityQuestionFeaturedChanged(question_id=self.id, is_featured=value))

    def increment_follower_count(self) -> None:
        """Called only by `ManageQuestionFollowersService.follow` in the
        same transaction that creates a `CommunityQuestionFollower` row.
        Deliberately does not call `touch()` — `updated_at` means
        "content last edited," and a follow is not a content edit — nor
        does it record its own event: the new `CommunityQuestionFollower`
        row's own `.create()` already records `CommunityQuestionFollowed`,
        so this method only mutates the counter."""
        self.follower_count += 1

    def decrement_follower_count(self, *, user_id: UUID) -> None:
        """Called only by `ManageQuestionFollowersService.unfollow`, in
        the same transaction that hard-deletes the `CommunityQuestionFollower`
        row. Unlike `increment_follower_count`, this *does* record an
        event: a hard-deleted join row raises none of its own (the same
        "hard delete, no historical value, no event" shape
        `CommunityPostTopic`/`CommunityPostTag`/`CommunityPostAttachment`
        removal already establishes), so `CommunityQuestion` itself — the
        aggregate that survives the operation — is the one that records
        `CommunityQuestionUnfollowed`. Still no `touch()`, for the same
        reason `increment_follower_count` skips it. Floors at zero
        defensively (never goes negative)."""
        self.follower_count = max(0, self.follower_count - 1)
        self.record_event(CommunityQuestionUnfollowed(question_id=self.id, user_id=user_id))


@dataclass(kw_only=True, eq=False)
class CommunityQuestionTopic(AggregateRoot):
    """A *secondary* topic assignment — `CommunityQuestion.primary_topic_id`
    is the mandatory primary topic stored directly on the aggregate root
    (this task's own DOMAIN section: "One primary Medical Topic" +
    "Optional secondary Medical Topics"); this join-row type exists only
    for the optional secondary ones."""

    question_id: QuestionId
    topic_id: UUID

    @classmethod
    def create(cls, *, question_id: QuestionId, topic_id: UUID) -> "CommunityQuestionTopic":
        assignment = cls(question_id=question_id, topic_id=topic_id)
        assignment.record_event(
            CommunityQuestionTopicAssigned(
                question_topic_id=assignment.id, question_id=question_id.value, topic_id=topic_id
            )
        )
        return assignment


@dataclass(kw_only=True, eq=False)
class CommunityQuestionTag(AggregateRoot):
    question_id: QuestionId
    tag: str

    @classmethod
    def create(cls, *, question_id: QuestionId, tag: str) -> "CommunityQuestionTag":
        normalized = tag.strip().lower()
        if not normalized:
            raise QuestionTagRequiredError()
        if len(normalized) > _TAG_MAX_LENGTH:
            raise QuestionTagTooLongError(_TAG_MAX_LENGTH)

        assignment = cls(question_id=question_id, tag=normalized)
        assignment.record_event(
            CommunityQuestionTagAssigned(
                question_tag_id=assignment.id, question_id=question_id.value, tag=normalized
            )
        )
        return assignment


@dataclass(kw_only=True, eq=False)
class CommunityQuestionAttachment(AggregateRoot):
    question_id: QuestionId
    document_id: UUID

    @classmethod
    def create(cls, *, question_id: QuestionId, document_id: UUID) -> "CommunityQuestionAttachment":
        attachment = cls(question_id=question_id, document_id=document_id)
        attachment.record_event(
            CommunityQuestionAttachmentAdded(
                attachment_id=attachment.id,
                question_id=question_id.value,
                document_id=document_id,
            )
        )
        return attachment


@dataclass(kw_only=True, eq=False)
class CommunityQuestionFollower(AggregateRoot):
    """Backs this task's own "Follower Count" FEATURES bullet — see
    `CommunityQuestion`'s own docstring for why this is a real entity
    (unlike `view_count`/`bookmark_count`/`share_count`, which stay pure
    declared counters)."""

    question_id: QuestionId
    user_id: UUID

    @classmethod
    def create(cls, *, question_id: QuestionId, user_id: UUID) -> "CommunityQuestionFollower":
        follower = cls(question_id=question_id, user_id=user_id)
        follower.record_event(
            CommunityQuestionFollowed(
                follower_id=follower.id, question_id=question_id.value, user_id=user_id
            )
        )
        return follower
