"""In-memory test doubles for the Community module's repositories and
Unit of Work — each implements the exact same interface its real
SQLAlchemy counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer service tests depend on these, never
on a real database.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import BinaryIO, Literal
from uuid import UUID

from app.modules.community.domain.entities import (
    Community,
    CommunityCategory,
    CommunityMember,
    CommunityRule,
    CommunityTag,
)
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.domain.repositories import (
    CommunityCategoryRepository,
    CommunityMemberRepository,
    CommunityRepository,
    CommunityRuleRepository,
    CommunityTagRepository,
)
from app.shared.application.storage_port import StoragePort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_VALUE_OBJECT_SORT_FIELDS = frozenset({"name", "slug"})


def _sort_key(
    community: Community, sort_by: str, member_counts: dict[UUID, int]
) -> str | int | datetime:
    """`Community.name`/`.slug` are value objects (no `__lt__` of their
    own), unlike the real `SqlAlchemyCommunityRepository.search`'s own
    `ORDER BY`, which sorts the underlying plain-`Text` column — casting
    to `str` here reproduces that same lexical ordering for the fake.
    `sort_by="member_count"` reproduces the real repository's `LEFT
    JOIN`/`GROUP BY` (see its own docstring) via `member_counts`, a
    plain dict tests populate through `set_member_count()` instead of
    constructing real `CommunityMember` rows."""
    if sort_by == "member_count":
        return member_counts.get(community.id, 0)
    if sort_by in _VALUE_OBJECT_SORT_FIELDS:
        value = getattr(community, sort_by, None)
        return str(value) if value is not None else ""
    timestamp = getattr(community, sort_by, None)
    return timestamp if isinstance(timestamp, datetime) else community.created_at


class FakeCommunityRepository(CommunityRepository):
    def __init__(self) -> None:
        self._communities: dict[UUID, Community] = {}
        self._member_counts: dict[UUID, int] = {}
        self._tag_assignments: dict[UUID, set[UUID]] = {}

    def set_member_count(self, community_id: UUID, count: int) -> None:
        """Test-only seam backing `sort_by="member_count"` — see
        `_sort_key`'s own docstring."""
        self._member_counts[community_id] = count

    def add_tag_assignment(self, community_id: UUID, tag_id: UUID) -> None:
        """Test-only seam backing `tag_ids` filtering — the real
        repository joins against `community_tag_assignments`
        (`SqlAlchemyCommunityTagRepository`'s own table); this fake
        tracks assignments directly instead of coordinating with a
        separate `FakeCommunityTagRepository` instance."""
        self._tag_assignments.setdefault(community_id, set()).add(tag_id)

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
        matches = [c for c in self._communities.values() if c.organization_id == organization_id]
        if visibilities:
            matches = [c for c in matches if c.visibility in visibilities]
        if category_id is not None:
            matches = [c for c in matches if c.category_id == category_id]
        if tag_ids:
            tag_id_set = set(tag_ids)
            matches = [c for c in matches if self._tag_assignments.get(c.id, set()) & tag_id_set]
        if featured_only:
            matches = [c for c in matches if c.is_featured]
        if verified_only:
            matches = [c for c in matches if c.is_verified]
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
        matches.sort(
            key=lambda c: _sort_key(c, sort_by, self._member_counts), reverse=sort_order == "desc"
        )
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

    async def count_active(self, community_id: UUID) -> int:
        return sum(
            1
            for m in self._members.values()
            if m.community_id.value == community_id and m.status is CommunityMemberStatus.ACTIVE
        )

    async def list_by_roles(
        self,
        community_id: UUID,
        roles: Sequence[CommunityRole],
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[CommunityMember]:
        role_set = set(roles)
        matches = [
            m
            for m in self._members.values()
            if m.community_id.value == community_id
            and m.role in role_set
            and m.status is CommunityMemberStatus.ACTIVE
        ]
        return matches[offset : offset + limit]

    async def add(self, member: CommunityMember) -> None:
        self._members[member.id] = member


class FakeCommunityCategoryRepository(CommunityCategoryRepository):
    def __init__(self) -> None:
        self._categories: dict[UUID, CommunityCategory] = {}

    async def get_by_id(self, category_id: UUID) -> CommunityCategory | None:
        return self._categories.get(category_id)

    async def get_by_slug(self, slug: str) -> CommunityCategory | None:
        for category in self._categories.values():
            if str(category.slug) == slug:
                return category
        return None

    async def get_by_name(self, name: str) -> CommunityCategory | None:
        for category in self._categories.values():
            if str(category.name) == name:
                return category
        return None

    async def list_active(self, *, offset: int = 0, limit: int = 100) -> list[CommunityCategory]:
        matches = [c for c in self._categories.values() if c.is_active]
        return matches[offset : offset + limit]

    async def add(self, category: CommunityCategory) -> None:
        self._categories[category.id] = category


class FakeCommunityTagRepository(CommunityTagRepository):
    def __init__(self) -> None:
        self._tags: dict[UUID, CommunityTag] = {}
        self._assignments: set[tuple[UUID, UUID]] = set()

    async def get_by_id(self, tag_id: UUID) -> CommunityTag | None:
        return self._tags.get(tag_id)

    async def get_by_name(self, name: str) -> CommunityTag | None:
        for tag in self._tags.values():
            if str(tag.name) == name:
                return tag
        return None

    async def search(
        self, term: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[CommunityTag], int]:
        normalized = term.strip().lower()
        matches = [t for t in self._tags.values() if normalized in str(t.name)]
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, tag: CommunityTag) -> None:
        self._tags[tag.id] = tag

    async def assign(self, community_id: UUID, tag_id: UUID) -> None:
        self._assignments.add((community_id, tag_id))

    async def unassign(self, community_id: UUID, tag_id: UUID) -> None:
        self._assignments.discard((community_id, tag_id))

    async def is_assigned(self, community_id: UUID, tag_id: UUID) -> bool:
        return (community_id, tag_id) in self._assignments

    async def list_for_community(self, community_id: UUID) -> list[CommunityTag]:
        tag_ids = {tid for cid, tid in self._assignments if cid == community_id}
        return [t for t in self._tags.values() if t.id in tag_ids]


class FakeCommunityRuleRepository(CommunityRuleRepository):
    def __init__(self) -> None:
        self._rules: dict[UUID, CommunityRule] = {}

    async def get_by_id(self, rule_id: UUID) -> CommunityRule | None:
        return self._rules.get(rule_id)

    async def list_by_community(
        self, community_id: UUID, *, include_disabled: bool = True
    ) -> list[CommunityRule]:
        matches = [r for r in self._rules.values() if r.community_id.value == community_id]
        if not include_disabled:
            matches = [r for r in matches if r.is_enabled]
        matches.sort(key=lambda r: r.position)
        return matches

    async def count_by_community(self, community_id: UUID) -> int:
        return sum(1 for r in self._rules.values() if r.community_id.value == community_id)

    async def add(self, rule: CommunityRule) -> None:
        self._rules[rule.id] = rule

    async def remove(self, rule_id: UUID) -> None:
        self._rules.pop(rule_id, None)


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


class FakeStoragePort(StoragePort):
    """In-memory `(bucket, object_name) -> bytes` store — the same shape
    `tests.unit.modules.documents.application.fakes.FakeStoragePort`
    already establishes for its own, identical need."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def upload(
        self, *, bucket: str, object_name: str, data: BinaryIO, content_type: str
    ) -> str:
        self.objects[(bucket, object_name)] = data.read()
        return object_name

    async def download(self, *, bucket: str, object_name: str) -> bytes:
        try:
            return self.objects[(bucket, object_name)]
        except KeyError as exc:
            raise FileNotFoundError(f"no object found at {bucket}/{object_name}") from exc

    async def delete(self, *, bucket: str, object_name: str) -> None:
        self.objects.pop((bucket, object_name), None)

    async def get_presigned_url(
        self, *, bucket: str, object_name: str, expires_seconds: int = 3600
    ) -> str:
        raise NotImplementedError
