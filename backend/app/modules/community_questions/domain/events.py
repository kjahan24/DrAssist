"""Domain events published by Community Questions module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork`.

Unlike `app.modules.community_posts.domain.events` (whose own docstring
notes post deletion raises no event, being a repository-level soft
delete), `CommunityQuestionDeleted` *does* exist — deletion here is a
business-visible status transition (`CommunityQuestion.delete()`), not an
infrastructure-only concern, see `QuestionStatus`'s own docstring.

View/bookmark/share counters raise no events: nothing in this module
increments them (no such use case is named in this task's own
APPLICATION section; see `CommunityQuestion`'s own docstring), so there
is no mutation path that would need one yet. `follower_count` is instead
mutated only as a side effect of `CommunityQuestionFollowed`/
`CommunityQuestionUnfollowed` themselves (see
`ManageQuestionFollowersService`'s own docstring) — those two events
double as the record of the count changing, so no separate "follower
count changed" event exists.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionCreated(DomainEvent):
    question_id: UUID
    community_id: UUID
    author_id: UUID
    slug: str
    title: str


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionUpdated(DomainEvent):
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionPublished(DomainEvent):
    question_id: UUID
    community_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionArchived(DomainEvent):
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionClosed(DomainEvent):
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionReopened(DomainEvent):
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionDeleted(DomainEvent):
    question_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionPinnedChanged(DomainEvent):
    question_id: UUID
    is_pinned: bool


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionFeaturedChanged(DomainEvent):
    question_id: UUID
    is_featured: bool


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionTopicAssigned(DomainEvent):
    question_topic_id: UUID
    question_id: UUID
    topic_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionTagAssigned(DomainEvent):
    question_tag_id: UUID
    question_id: UUID
    tag: str


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionAttachmentAdded(DomainEvent):
    attachment_id: UUID
    question_id: UUID
    document_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionFollowed(DomainEvent):
    follower_id: UUID
    question_id: UUID
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityQuestionUnfollowed(DomainEvent):
    question_id: UUID
    user_id: UUID
