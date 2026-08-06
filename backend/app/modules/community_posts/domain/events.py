"""Domain events published by Community Posts module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork`.

`CommunityPost` deletion deliberately raises no event: it is a
repository-level soft delete (`CommunityPostRepository.remove`), the same
"no domain entity mutation, so nothing to record an event from" shape
`app.modules.community.domain.events`/`app.modules.medical_topics.domain
.events` already establish for their own aggregate deletion.

View/bookmark/share counters raise no events either — nothing in this
module increments them (no such use case is named in this task's own
APPLICATION section; see `CommunityPost`'s own docstring), so there is
no mutation path that would need one yet.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CommunityPostCreated(DomainEvent):
    post_id: UUID
    community_id: UUID
    author_id: UUID
    slug: str
    title: str


@dataclass(frozen=True, kw_only=True)
class CommunityPostUpdated(DomainEvent):
    post_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityPostPublished(DomainEvent):
    post_id: UUID
    community_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityPostArchived(DomainEvent):
    post_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityPostPinnedChanged(DomainEvent):
    post_id: UUID
    is_pinned: bool


@dataclass(frozen=True, kw_only=True)
class CommunityPostLockedChanged(DomainEvent):
    post_id: UUID
    is_locked: bool


@dataclass(frozen=True, kw_only=True)
class CommunityPostFeaturedChanged(DomainEvent):
    post_id: UUID
    is_featured: bool


@dataclass(frozen=True, kw_only=True)
class CommunityPostTopicAssigned(DomainEvent):
    post_topic_id: UUID
    post_id: UUID
    topic_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityPostTagAssigned(DomainEvent):
    post_tag_id: UUID
    post_id: UUID
    tag: str


@dataclass(frozen=True, kw_only=True)
class CommunityPostAttachmentAdded(DomainEvent):
    attachment_id: UUID
    post_id: UUID
    document_id: UUID
