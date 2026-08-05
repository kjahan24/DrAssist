"""Domain events published by Community module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.

`Community` deletion deliberately raises no event: it is a repository-
level soft delete (`CommunityRepository.remove`), the same "no domain
entity mutation, so nothing to record an event from" shape
`app.modules.authentication.infrastructure.repositories` already
establishes for its own row-level revokes — see that repository's own
module docstring.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CommunityCreated(DomainEvent):
    community_id: UUID
    organization_id: UUID
    slug: str
    name: str


@dataclass(frozen=True, kw_only=True)
class CommunityUpdated(DomainEvent):
    community_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityMemberJoined(DomainEvent):
    community_id: UUID
    user_id: UUID
    role: str


@dataclass(frozen=True, kw_only=True)
class CommunityMemberLeft(DomainEvent):
    community_id: UUID
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityAppearanceUpdated(DomainEvent):
    community_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityFeaturedChanged(DomainEvent):
    community_id: UUID
    is_featured: bool


@dataclass(frozen=True, kw_only=True)
class CommunityVerifiedChanged(DomainEvent):
    community_id: UUID
    is_verified: bool


@dataclass(frozen=True, kw_only=True)
class CommunityCategoryAssigned(DomainEvent):
    community_id: UUID
    category_id: UUID | None


@dataclass(frozen=True, kw_only=True)
class CommunityCategoryCreated(DomainEvent):
    category_id: UUID
    name: str


@dataclass(frozen=True, kw_only=True)
class CommunityTagCreated(DomainEvent):
    tag_id: UUID
    name: str


@dataclass(frozen=True, kw_only=True)
class CommunityRuleCreated(DomainEvent):
    rule_id: UUID
    community_id: UUID
    title: str


@dataclass(frozen=True, kw_only=True)
class CommunityRuleUpdated(DomainEvent):
    rule_id: UUID
    community_id: UUID


@dataclass(frozen=True, kw_only=True)
class CommunityRuleEnabledChanged(DomainEvent):
    rule_id: UUID
    community_id: UUID
    is_enabled: bool


@dataclass(frozen=True, kw_only=True)
class CommunityRulesReordered(DomainEvent):
    community_id: UUID
    rule_ids: tuple[UUID, ...]
