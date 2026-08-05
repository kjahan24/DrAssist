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

from app.modules.community.domain.entities import (
    Community,
    CommunityCategory,
    CommunityMember,
    CommunityRule,
    CommunityTag,
)
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
        category_id: UUID | None = None,
        tag_ids: Sequence[UUID] | None = None,
        featured_only: bool = False,
        verified_only: bool = False,
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
        communities, backing `ListCommunitiesService`/
        `BrowseCommunitiesService`. `query` combines full-text search
        over `name`/`description` with a partial match on `name` — the
        same `apply_combined_text_search` shape every other module's own
        `search()` already uses. `category_id`/`tag_ids`/`featured_only`/
        `verified_only` are this task's own Browse-by-facet filters,
        added additively (all default to "no filter"), so every call
        site built in Phase 5.1 keeps working unchanged. `sort_by` also
        now accepts `"member_count"` (see `BrowseCommunitiesService`'s
        own "popular" sort docstring) — the SQLAlchemy implementation
        handles that case with a `LEFT JOIN`/`GROUP BY` rather than the
        plain column lookup every other `sort_by` value uses. Returns
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
    async def count_active(self, community_id: UUID) -> int:
        """Total `ACTIVE` member count — backs `CommunityStatisticsService`
        and this task's own "Member count" feature."""
        ...

    @abstractmethod
    async def list_by_roles(
        self,
        community_id: UUID,
        roles: Sequence[CommunityRole],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[CommunityMember]:
        """`ACTIVE` members holding any of `roles` — backs this task's
        own "Community moderators" feature
        (`roles=(MODERATOR, ADMIN, OWNER)`); moderators are not a
        separate entity, just members whose own `CommunityRole` already
        carries that meaning (see `CommunityRole`'s own docstring)."""
        ...

    @abstractmethod
    async def add(self, member: CommunityMember) -> None: ...


class CommunityCategoryRepository(ABC):
    @abstractmethod
    async def get_by_id(self, category_id: UUID) -> CommunityCategory | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> CommunityCategory | None: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> CommunityCategory | None: ...

    @abstractmethod
    async def list_active(self, *, offset: int = 0, limit: int = 100) -> list[CommunityCategory]:
        """Categories are a small, platform-wide (not organization-scoped)
        vocabulary — see `CommunityCategory`'s own docstring — so this
        lists across every organization, not one tenant's own."""
        ...

    @abstractmethod
    async def add(self, category: CommunityCategory) -> None: ...


class CommunityTagRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tag_id: UUID) -> CommunityTag | None: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> CommunityTag | None: ...

    @abstractmethod
    async def search(
        self, term: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[CommunityTag], int]:
        """Case-insensitive partial match on `CommunityTag.name` — this
        task's own "Tags... Searchable" requirement (typeahead/autocomplete
        when assigning a tag to a community)."""
        ...

    @abstractmethod
    async def add(self, tag: CommunityTag) -> None: ...

    @abstractmethod
    async def assign(self, community_id: UUID, tag_id: UUID) -> None:
        """Insert one `community_tags` join row — a no-op (not an error)
        if already assigned, mirroring `CommunityRepository.add`'s own
        upsert idempotence; the *caller* (`ManageCommunityTagsService`)
        is what raises `CommunityTagAlreadyAssignedError` when it wants
        that to be an error, by checking `is_assigned` first."""
        ...

    @abstractmethod
    async def unassign(self, community_id: UUID, tag_id: UUID) -> None: ...

    @abstractmethod
    async def is_assigned(self, community_id: UUID, tag_id: UUID) -> bool: ...

    @abstractmethod
    async def list_for_community(self, community_id: UUID) -> list[CommunityTag]: ...


class CommunityRuleRepository(ABC):
    @abstractmethod
    async def get_by_id(self, rule_id: UUID) -> CommunityRule | None: ...

    @abstractmethod
    async def list_by_community(
        self, community_id: UUID, *, include_disabled: bool = True
    ) -> list[CommunityRule]:
        """Ordered by `CommunityRule.position` ascending."""
        ...

    @abstractmethod
    async def count_by_community(self, community_id: UUID) -> int: ...

    @abstractmethod
    async def add(self, rule: CommunityRule) -> None: ...

    @abstractmethod
    async def remove(self, rule_id: UUID) -> None:
        """Hard delete — rules carry no historical/audit value once
        removed, unlike `Community` itself (soft-deleted) or
        `CommunityMember` (status-cycled); a no-op if already missing."""
        ...
