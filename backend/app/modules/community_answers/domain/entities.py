"""Community Answers module aggregate roots: CommunityAnswer,
CommunityAnswerRevision, CommunityAnswerAttachment.

Each is its own aggregate — every reference to another aggregate,
including cross-module ones (`question_id` -> CommunityQuestion,
`community_id` -> Community, `topic_id` -> MedicalTopic, `author_id`/
`updated_by` -> User, `document_id` -> MedicalDocument), is by ID only,
never by object reference — the same rule `app.modules.community_questions
.domain.entities` already follows. Cross-module ID references are
validated by the application layer via that peer module's own public
query port (`CommunityQueryPort`/`QuestionQueryPort`/`DocumentQueryPort`),
never by importing across `domain/` packages.

`CommunityAnswer.community_id`/`.organization_id`/`.topic_id` are all
stored directly (denormalized from the parent `CommunityQuestion` at
creation time by `CreateAnswerService`, via `QuestionQueryPort
.get_question_summary` — which already returns `community_id`/
`organization_id`/`primary_topic_id`), not resolved via a `question_id`
join on every query — the same "tenant id stored directly on the
tenant-scoped row" shape `CommunityQuestion.organization_id` already
establishes. `topic_id` specifically mirrors only the parent question's
own mandatory *primary* topic, not any secondary topic assignment — see
`CreateAnswerService`'s own docstring for why extending
`QuestionQueryPort` to also expose secondary-topic lookups was
deliberately avoided as unnecessary for what this task's own QUERY/
FILTERING section actually asks for ("Medical Topic", singular).

`view_count`/`share_count` are declared fields only — this task's own
APPLICATION section names no "record a view/share" use case, so nothing
in this module increments them yet, matching `CommunityPost`/
`CommunityQuestion`'s own identical reasoning.

`CommunityAnswerAttachment` enforces no soft-delete: a row is either
present or absent, never edited — the same "hard delete, no historical
value" shape `CommunityQuestionAttachment` already establishes.
`CommunityAnswerRevision` is the opposite: append-only and genuinely
immutable — see its own docstring and `CommunityAnswerRevisionRepository`'s
own docstring for why that repository has no `remove()` method at all.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.domain.events import (
    CommunityAnswerArchived,
    CommunityAnswerAttachmentAdded,
    CommunityAnswerBestRemoved,
    CommunityAnswerCreated,
    CommunityAnswerDeleted,
    CommunityAnswerFeaturedChanged,
    CommunityAnswerMarkedBest,
    CommunityAnswerPinnedChanged,
    CommunityAnswerPublished,
    CommunityAnswerRestored,
    CommunityAnswerRevisionCreated,
    CommunityAnswerUpdated,
)
from app.modules.community_answers.domain.exceptions import (
    AnswerAlreadyArchivedError,
    AnswerAlreadyBestAnswerError,
    AnswerAlreadyDeletedError,
    AnswerAlreadyPublishedError,
    AnswerCannotBeRestoredError,
    AnswerNotBestAnswerError,
    AnswerNotPublishedForBestAnswerError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerId, AnswerSummary
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class CommunityAnswer(AggregateRoot):
    question_id: UUID
    community_id: UUID
    organization_id: UUID
    topic_id: UUID
    author_id: UUID
    body: AnswerBody
    summary: AnswerSummary
    status: AnswerStatus = AnswerStatus.DRAFT
    visibility: AnswerVisibility = AnswerVisibility.PUBLIC
    is_anonymous: bool = False
    is_best_answer: bool = False
    is_featured: bool = False
    is_pinned: bool = False
    view_count: int = 0
    share_count: int = 0
    revision_number: int = 1
    published_at: datetime | None = None
    updated_by: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        question_id: UUID,
        community_id: UUID,
        organization_id: UUID,
        topic_id: UUID,
        author_id: UUID,
        body: AnswerBody,
        summary: AnswerSummary | None = None,
        visibility: AnswerVisibility = AnswerVisibility.PUBLIC,
        is_anonymous: bool = False,
    ) -> "CommunityAnswer":
        answer = cls(
            question_id=question_id,
            community_id=community_id,
            organization_id=organization_id,
            topic_id=topic_id,
            author_id=author_id,
            body=body,
            summary=summary if summary is not None else AnswerSummary.from_body(str(body)),
            visibility=visibility,
            is_anonymous=is_anonymous,
            updated_by=author_id,
        )
        answer.record_event(
            CommunityAnswerCreated(
                answer_id=answer.id, question_id=question_id, author_id=author_id
            )
        )
        return answer

    def update_content(
        self,
        *,
        body: AnswerBody | None = None,
        summary: AnswerSummary | None = None,
        regenerate_summary: bool = False,
        updated_by: UUID | None = None,
    ) -> "CommunityAnswerRevision | None":
        """Returns the archived snapshot of the *previous* body as a
        `CommunityAnswerRevision`, or `None` if no revision was needed —
        a revision is only recorded when `body` is actually changing
        *and* the answer is currently `PUBLISHED` (this task's own
        REVISION HISTORY section: "Every published answer edit must
        preserve revision history" — a draft has never been publicly
        visible, so editing it before its first publish has nothing
        worth preserving). The caller (`UpdateAnswerService`) is
        responsible for persisting the returned revision through
        `CommunityAnswerRevisionRepository.add` in the same transaction
        — this method only decides *whether* one is needed and
        constructs it; it never touches a repository itself."""
        revision = None
        if (
            body is not None
            and str(body) != str(self.body)
            and self.status is AnswerStatus.PUBLISHED
        ):
            revision = CommunityAnswerRevision.create(
                answer_id=AnswerId(self.id),
                revision_number=self.revision_number,
                previous_body=str(self.body),
                author_id=updated_by if updated_by is not None else self.author_id,
            )
            self.revision_number += 1

        if body is not None:
            self.body = body
        if summary is not None:
            self.summary = summary
        elif regenerate_summary:
            self.summary = AnswerSummary.from_body(str(self.body))
        if updated_by is not None:
            self.updated_by = updated_by

        self.touch()
        self.record_event(CommunityAnswerUpdated(answer_id=self.id))
        return revision

    def publish(self) -> None:
        if self.status is AnswerStatus.PUBLISHED:
            raise AnswerAlreadyPublishedError(self.id)
        self.status = AnswerStatus.PUBLISHED
        self.published_at = datetime.now(UTC)
        self.touch()
        self.record_event(CommunityAnswerPublished(answer_id=self.id, question_id=self.question_id))

    def archive(self) -> None:
        """Clears a stale `is_best_answer` flag as part of archiving —
        see this class's own module docstring and `CommunityAnswerBestRemoved`'s
        own docstring for why: this task's own DOMAIN section requires
        that "deleting/archiving the Best Answer must safely clear ...
        the Best Answer state," and silently clearing it here (rather
        than blocking the archive action outright) is the least
        surprising choice — a moderator archiving outdated content
        should never be blocked by a stale "best answer" flag."""
        if self.status is AnswerStatus.ARCHIVED:
            raise AnswerAlreadyArchivedError(self.id)
        if self.is_best_answer:
            self.is_best_answer = False
            self.record_event(
                CommunityAnswerBestRemoved(answer_id=self.id, question_id=self.question_id)
            )
        self.status = AnswerStatus.ARCHIVED
        self.touch()
        self.record_event(CommunityAnswerArchived(answer_id=self.id))

    def restore(self) -> None:
        """The recovery action for `ARCHIVED`/`DELETED` answers — always
        lands on `DRAFT`, never straight back to `PUBLISHED`, so
        re-exposing restored content is always a separate, explicit
        `publish()` call rather than an implicit side effect of
        restoring."""
        if self.status not in (AnswerStatus.ARCHIVED, AnswerStatus.DELETED):
            raise AnswerCannotBeRestoredError(self.id)
        self.status = AnswerStatus.DRAFT
        self.touch()
        self.record_event(CommunityAnswerRestored(answer_id=self.id))

    def delete(self) -> None:
        """Business-visible soft delete via status transition — see
        `AnswerStatus`'s own docstring. Clears a stale `is_best_answer`
        flag the same way `archive()` does — see that method's own
        docstring."""
        if self.status is AnswerStatus.DELETED:
            raise AnswerAlreadyDeletedError(self.id)
        if self.is_best_answer:
            self.is_best_answer = False
            self.record_event(
                CommunityAnswerBestRemoved(answer_id=self.id, question_id=self.question_id)
            )
        self.status = AnswerStatus.DELETED
        self.touch()
        self.record_event(CommunityAnswerDeleted(answer_id=self.id))

    def set_featured(self, value: bool) -> None:
        """Platform/community-level curation flag — the same
        `set_featured` shape `CommunityPost`/`CommunityQuestion` already
        establish for themselves."""
        if self.is_featured is value:
            return
        self.is_featured = value
        self.touch()
        self.record_event(CommunityAnswerFeaturedChanged(answer_id=self.id, is_featured=value))

    def set_pinned(self, value: bool) -> None:
        """Sticky-within-its-own-question ordering — the same
        `set_pinned` shape `CommunityPost`/`CommunityQuestion` already
        establish for themselves, scoped here to how an answer sorts
        within its own question's answer list."""
        if self.is_pinned is value:
            return
        self.is_pinned = value
        self.touch()
        self.record_event(CommunityAnswerPinnedChanged(answer_id=self.id, is_pinned=value))

    def mark_as_best(self) -> None:
        """Only a `PUBLISHED` answer may become the best answer — this
        task's own DOMAIN section: "Only valid published answers can
        become Best Answer." The "only one best answer per question"
        invariant is *not* enforced here (a single aggregate cannot see
        its sibling rows) — see `MarkBestAnswerService`'s own docstring
        for where that coordination actually happens."""
        if self.status is not AnswerStatus.PUBLISHED:
            raise AnswerNotPublishedForBestAnswerError(self.id)
        if self.is_best_answer:
            raise AnswerAlreadyBestAnswerError(self.id)
        self.is_best_answer = True
        self.touch()
        self.record_event(
            CommunityAnswerMarkedBest(answer_id=self.id, question_id=self.question_id)
        )

    def remove_best(self) -> None:
        if not self.is_best_answer:
            raise AnswerNotBestAnswerError(self.id)
        self.is_best_answer = False
        self.touch()
        self.record_event(
            CommunityAnswerBestRemoved(answer_id=self.id, question_id=self.question_id)
        )


@dataclass(kw_only=True, eq=False)
class CommunityAnswerRevision(AggregateRoot):
    """An immutable, append-only snapshot of an answer's *previous*
    content, taken automatically by `CommunityAnswer.update_content`
    whenever a published answer's body actually changes — see that
    method's own docstring. Never mutated or removed once created; see
    `CommunityAnswerRevisionRepository`'s own docstring."""

    answer_id: AnswerId
    revision_number: int
    previous_body: str
    author_id: UUID

    @classmethod
    def create(
        cls, *, answer_id: AnswerId, revision_number: int, previous_body: str, author_id: UUID
    ) -> "CommunityAnswerRevision":
        revision = cls(
            answer_id=answer_id,
            revision_number=revision_number,
            previous_body=previous_body,
            author_id=author_id,
        )
        revision.record_event(
            CommunityAnswerRevisionCreated(
                revision_id=revision.id,
                answer_id=answer_id.value,
                revision_number=revision_number,
            )
        )
        return revision


@dataclass(kw_only=True, eq=False)
class CommunityAnswerAttachment(AggregateRoot):
    answer_id: AnswerId
    document_id: UUID

    @classmethod
    def create(cls, *, answer_id: AnswerId, document_id: UUID) -> "CommunityAnswerAttachment":
        attachment = cls(answer_id=answer_id, document_id=document_id)
        attachment.record_event(
            CommunityAnswerAttachmentAdded(
                attachment_id=attachment.id, answer_id=answer_id.value, document_id=document_id
            )
        )
        return attachment
