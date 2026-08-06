"""Domain events published by Medical Topics module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork`.

`MedicalTopic` deletion deliberately raises no event: it is a repository-
level soft delete (`MedicalTopicRepository.remove`), the same "no domain
entity mutation, so nothing to record an event from" shape
`app.modules.community.domain.events` already establishes for
`Community` deletion — see that module's own docstring.

`MedicalTopic.update_trending_score`/`update_popularity_score` also raise
no event — these are recomputed frequently (e.g. by a periodic background
job), and an event per recalculation would flood the event bus with no
consumer that needs one yet, the same "no event for a purely
positional/computed update" reasoning `CommunityRule.reposition` already
establishes for itself.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MedicalTopicCreated(DomainEvent):
    topic_id: UUID
    slug: str
    name: str


@dataclass(frozen=True, kw_only=True)
class MedicalTopicUpdated(DomainEvent):
    topic_id: UUID


@dataclass(frozen=True, kw_only=True)
class MedicalTopicFeaturedChanged(DomainEvent):
    topic_id: UUID
    is_featured: bool


@dataclass(frozen=True, kw_only=True)
class TopicFollowed(DomainEvent):
    topic_id: UUID
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class TopicSpecialtyCreated(DomainEvent):
    specialty_id: UUID
    name: str


@dataclass(frozen=True, kw_only=True)
class MedicalTopicAliasCreated(DomainEvent):
    alias_id: UUID
    topic_id: UUID
    alias: str


@dataclass(frozen=True, kw_only=True)
class MedicalTopicRelationCreated(DomainEvent):
    relation_id: UUID
    topic_id: UUID
    related_topic_id: UUID
