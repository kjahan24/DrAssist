"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.medical_topics.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method on any interface: a repository returns the actual
aggregate object, the caller mutates it via its own methods, and the Unit
of Work's `commit()` persists the change through SQLAlchemy's
session-level change tracking — `add()` is upsert (insert-or-overwrite),
the same shape every other module's repository already uses.

This module is deliberately platform-wide, not organization-scoped — see
`app.modules.medical_topics.domain.enums.TopicVisibility`'s own
docstring — so no method here takes an `organization_id`, unlike
`app.modules.community.domain.repositories.CommunityRepository`.

`MedicalTopicFollowerRepository`/`MedicalTopicAliasRepository`/
`MedicalTopicRelationRepository` enforce no soft-delete: a follow/alias/
relation is either present or absent, never edited, the same "hard
delete, no historical value" shape
`app.modules.community.domain.repositories.CommunityRuleRepository`
already establishes for `CommunityRule.remove`.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from app.modules.medical_topics.domain.entities import (
    MedicalTopic,
    MedicalTopicAlias,
    MedicalTopicFollower,
    MedicalTopicRelation,
    TopicSpecialty,
)
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility


class MedicalTopicRepository(ABC):
    @abstractmethod
    async def get_by_id(self, topic_id: UUID) -> MedicalTopic | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> MedicalTopic | None: ...

    @abstractmethod
    async def list_children(
        self, parent_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopic]: ...

    @abstractmethod
    async def search(
        self,
        *,
        query: str | None = None,
        status: Sequence[TopicStatus] | None = None,
        visibility: Sequence[TopicVisibility] | None = None,
        specialty_id: UUID | None = None,
        parent_id: UUID | None = None,
        featured_only: bool = False,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[MedicalTopic], int]:
        """Search & Filtering: platform-wide search over topics, backing
        `ListTopicsService`/`SearchTopicsService`/`TrendingTopicsService`/
        `FeaturedTopicsService`. `query` combines full-text search over
        `name`/`description` with a partial match on `name` — the same
        `apply_combined_text_search` shape every other module's own
        `search()` already uses. `sort_by` accepts any of `"created_at"`,
        `"updated_at"`, `"name"`, `"trending_score"`, `"popularity_score"`
        — all plain columns on this same table (no join/subquery needed,
        unlike `CommunityRepository.search`'s own `"member_count"` case).
        Returns `(page_of_topics, total_matching_count)`."""
        ...

    @abstractmethod
    async def list_by_ids(self, topic_ids: Sequence[UUID]) -> list[MedicalTopic]:
        """Batch lookup, order not guaranteed — backs
        `RelatedTopicsService`, which resolves a set of related-topic ids
        from `MedicalTopicRelationRepository` into full summaries in one
        round trip rather than N+1 `get_by_id` calls."""
        ...

    @abstractmethod
    async def add(self, topic: MedicalTopic) -> None: ...

    @abstractmethod
    async def remove(self, topic_id: UUID) -> None:
        """Soft-delete: sets `deleted_at` directly at the infrastructure
        level without loading/mutating the domain entity — the same
        shape `CommunityRepository.remove` already uses; a no-op if
        already deleted or missing."""
        ...


class MedicalTopicFollowerRepository(ABC):
    @abstractmethod
    async def get_by_topic_and_user(
        self, topic_id: UUID, user_id: UUID
    ) -> MedicalTopicFollower | None: ...

    @abstractmethod
    async def list_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopicFollower]: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopicFollower]: ...

    @abstractmethod
    async def count_by_topic(self, topic_id: UUID) -> int: ...

    @abstractmethod
    async def add(self, follower: MedicalTopicFollower) -> None: ...

    @abstractmethod
    async def remove(self, topic_id: UUID, user_id: UUID) -> None:
        """A no-op if the follow relationship doesn't exist — the
        *caller* (`UnfollowTopicService`) is what raises
        `TopicNotFollowedError` when it wants that to be an error, by
        checking `get_by_topic_and_user` first, the same split
        `CommunityTagRepository.unassign`/`ManageCommunityTagsService
        .unassign_tag` already establishes."""
        ...


class MedicalTopicAliasRepository(ABC):
    @abstractmethod
    async def get_by_id(self, alias_id: UUID) -> MedicalTopicAlias | None: ...

    @abstractmethod
    async def list_by_topic(self, topic_id: UUID) -> list[MedicalTopicAlias]: ...

    @abstractmethod
    async def search_by_alias(
        self, term: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[MedicalTopicAlias], int]:
        """Case-insensitive partial match on `MedicalTopicAlias.alias` —
        backs `SearchTopicsService`'s own "match on alias/synonym, not
        just the canonical name" behavior."""
        ...

    @abstractmethod
    async def add(self, alias: MedicalTopicAlias) -> None: ...

    @abstractmethod
    async def remove(self, alias_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...


class MedicalTopicRelationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, relation_id: UUID) -> MedicalTopicRelation | None: ...

    @abstractmethod
    async def list_related(self, topic_id: UUID) -> list[MedicalTopicRelation]:
        """Relations are queried symmetrically — a row `(A, B)` makes B
        appear in A's related list *and* A appear in B's, without storing
        the reverse row too (`WHERE topic_id = :id OR related_topic_id =
        :id` at the infrastructure level) — see `RelatedTopicsService`'s
        own docstring for why this avoids double-insertion/consistency
        bookkeeping a stored-both-directions approach would need."""
        ...

    @abstractmethod
    async def exists(self, topic_id: UUID, related_topic_id: UUID) -> bool:
        """Symmetric existence check — `(A, B)` and `(B, A)` are the same
        relation for this purpose (see `list_related`'s own docstring)."""
        ...

    @abstractmethod
    async def add(self, relation: MedicalTopicRelation) -> None: ...

    @abstractmethod
    async def remove(self, relation_id: UUID) -> None:
        """Hard delete — a no-op if already missing."""
        ...


class TopicSpecialtyRepository(ABC):
    @abstractmethod
    async def get_by_id(self, specialty_id: UUID) -> TopicSpecialty | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> TopicSpecialty | None: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> TopicSpecialty | None: ...

    @abstractmethod
    async def list_active(self, *, offset: int = 0, limit: int = 100) -> list[TopicSpecialty]: ...

    @abstractmethod
    async def add(self, specialty: TopicSpecialty) -> None: ...
