"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.community.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method on either interface: a repository returns the
actual aggregate object, the caller mutates it via its own methods, and
the Unit of Work's `commit()` persists the change through SQLAlchemy's
session-level change tracking — `add()` is upsert (insert-or-overwrite),
the same shape every other module's repository already uses.

`CommunityMemberRepository` enforces no soft-delete: a membership row is
created once per `(community_id, user_id)` pair and its `status` cycles
between `ACTIVE`/`LEFT` (see `CommunityMember.leave`/`rejoin`) rather than
the row ever being removed — `LEFT` already *is* this aggregate's "soft
delete", so there is deliberately no `remove()` method here, unlike
`CommunityRepository.remove` (`Community` itself uses the codebase-wide
`deleted_at` soft-delete convention).
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityRole, CommunityVisibility


class CommunityRepository(ABC):
    @abstractmethod
    async def get_by_id(self, community_id: UUID) -> Community | None: ...

    @abstractmethod
    async def get_by_slug(self, organization_id: UUID, slug: str) -> Community | None: ...

    @abstractmethod
    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Community]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        visibilities: Sequence[CommunityVisibility] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Community], int]:
        """Search & Filtering: organization-scoped search over
        communities, backing `ListCommunitiesService`. `query` combines
        full-text search over `name`/`description` with a partial match
        on `name` — the same `apply_combined_text_search` shape every
        other module's own `search()` already uses. Returns
        `(page_of_communities, total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, community: Community) -> None: ...

    @abstractmethod
    async def remove(self, community_id: UUID) -> None:
        """Soft-delete: sets `deleted_at` directly at the infrastructure
        level without loading/mutating the domain entity — the same
        shape `app.modules.authentication.infrastructure.repositories`
        already uses for its own row-level revokes (see that module's
        own docstring); a no-op if already deleted or missing."""
        ...


class CommunityMemberRepository(ABC):
    @abstractmethod
    async def get_by_id(self, member_id: UUID) -> CommunityMember | None: ...

    @abstractmethod
    async def get_by_community_and_user(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMember | None: ...

    @abstractmethod
    async def list_by_community(
        self, community_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityMember]: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityMember]: ...

    @abstractmethod
    async def count_active_by_role(self, community_id: UUID, role: CommunityRole) -> int:
        """How many `ACTIVE` members of `community_id` currently hold
        `role` — `LeaveCommunityService` uses this (with
        `role=CommunityRole.OWNER`) to enforce "a community must always
        retain at least one owner" before letting an owner leave."""
        ...

    @abstractmethod
    async def add(self, member: CommunityMember) -> None: ...
