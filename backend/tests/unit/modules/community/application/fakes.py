"""In-memory test doubles for the Community module's repositories and
Unit of Work — each implements the exact same interface its real
SQLAlchemy counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer service tests depend on these, never
on a real database.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.domain.repositories import CommunityMemberRepository, CommunityRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_VALUE_OBJECT_SORT_FIELDS = frozenset({"name", "slug"})


def _sort_key(community: Community, sort_by: str) -> str | datetime:
    """`Community.name`/`.slug` are value objects (no `__lt__` of their
    own), unlike the real `SqlAlchemyCommunityRepository.search`'s own
    `ORDER BY`, which sorts the underlying plain-`Text` column — casting
    to `str` here reproduces that same lexical ordering for the fake."""
    if sort_by in _VALUE_OBJECT_SORT_FIELDS:
        value = getattr(community, sort_by, None)
        return str(value) if value is not None else ""
    timestamp = getattr(community, sort_by, None)
    return timestamp if isinstance(timestamp, datetime) else community.created_at


class FakeCommunityRepository(CommunityRepository):
    def __init__(self) -> None:
        self._communities: dict[UUID, Community] = {}

    async def get_by_id(self, community_id: UUID) -> Community | None:
        return self._communities.get(community_id)

    async def get_by_slug(self, organization_id: UUID, slug: str) -> Community | None:
        normalized = slug.strip().lower()
        for community in self._communities.values():
            if community.organization_id == organization_id and str(community.slug) == normalized:
                return community
        return None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Community]:
        matches = [c for c in self._communities.values() if c.organization_id == organization_id]
        return matches[offset : offset + limit]

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
        matches = [c for c in self._communities.values() if c.organization_id == organization_id]
        if visibilities:
            matches = [c for c in matches if c.visibility in visibilities]
        if created_from is not None:
            matches = [c for c in matches if c.created_at >= created_from]
        if created_to is not None:
            matches = [c for c in matches if c.created_at <= created_to]
        if updated_from is not None:
            matches = [c for c in matches if c.updated_at >= updated_from]
        if updated_to is not None:
            matches = [c for c in matches if c.updated_at <= updated_to]
        if query:
            term = query.strip().lower()
            matches = [
                c
                for c in matches
                if term in str(c.name).lower()
                or (c.description is not None and term in str(c.description).lower())
            ]
        matches.sort(key=lambda c: _sort_key(c, sort_by), reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, community: Community) -> None:
        self._communities[community.id] = community

    async def remove(self, community_id: UUID) -> None:
        self._communities.pop(community_id, None)


class FakeCommunityMemberRepository(CommunityMemberRepository):
    def __init__(self) -> None:
        self._members: dict[UUID, CommunityMember] = {}

    async def get_by_id(self, member_id: UUID) -> CommunityMember | None:
        return self._members.get(member_id)

    async def get_by_community_and_user(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMember | None:
        for member in self._members.values():
            if member.community_id.value == community_id and member.user_id == user_id:
                return member
        return None

    async def list_by_community(
        self, community_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityMember]:
        matches = [m for m in self._members.values() if m.community_id.value == community_id]
        return matches[offset : offset + limit]

    async def list_by_user(
        self, user_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityMember]:
        matches = [m for m in self._members.values() if m.user_id == user_id]
        return matches[offset : offset + limit]

    async def count_active_by_role(self, community_id: UUID, role: CommunityRole) -> int:
        return sum(
            1
            for m in self._members.values()
            if m.community_id.value == community_id
            and m.role is role
            and m.status is CommunityMemberStatus.ACTIVE
        )

    async def add(self, member: CommunityMember) -> None:
        self._members[member.id] = member


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass
