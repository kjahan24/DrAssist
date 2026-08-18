"""Domain events published by Community Answers module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork`.

Like `app.modules.community_questions.domain.events
.CommunityQuestionDeleted`, `CommunityAnswerDeleted` *does* exist —
deletion here is a business-visible status transition
(`CommunityAnswer.delete()`), not an infrastructure-only concern, see
`AnswerStatus`'s own docstring.

`view_count`/`share_count` raise no events: nothing in this module
increments them (no such use case is named in this task's own
APPLICATION section, mirroring the identical `CommunityPost`/
`CommunityQuestion` reasoning for their own declared-only counters).

`CommunityAnswerBestRemoved` can be published for two different reasons:
an explicit `RemoveBestAnswerService` call, or as an automatic side
effect of `archive()`/`delete()` clearing a stale best-answer flag — see
those methods' own docstrings.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerCreated(DomainEvent):
    answer_id: UUID
    question_id: UUID
    author_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerUpdated(DomainEvent):
    answer_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerPublished(DomainEvent):
    answer_id: UUID
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerArchived(DomainEvent):
    answer_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerRestored(DomainEvent):
    answer_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerDeleted(DomainEvent):
    answer_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerMarkedBest(DomainEvent):
    answer_id: UUID
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerBestRemoved(DomainEvent):
    answer_id: UUID
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerFeaturedChanged(DomainEvent):
    answer_id: UUID
    is_featured: bool


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerPinnedChanged(DomainEvent):
    answer_id: UUID
    is_pinned: bool


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerRevisionCreated(DomainEvent):
    revision_id: UUID
    answer_id: UUID
    revision_number: int


@dataclass(frozen=True, kw_only=True)
class CommunityAnswerAttachmentAdded(DomainEvent):
    attachment_id: UUID
    answer_id: UUID
    document_id: UUID
