"""Community module aggregate roots: Community, CommunityMember.

Each is its own aggregate — `CommunityMember` references `Community` by
ID only (`community_id: CommunityId`), never by object reference, the
same rule `app.modules.organization.domain.entities.Department` already
follows for its own `organization_id: UUID` reference to `Organization`.
All mutation goes through named methods that enforce the aggregate's own
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.domain.events import (
    CommunityCreated,
    CommunityMemberJoined,
    CommunityMemberLeft,
    CommunityUpdated,
)
from app.modules.community.domain.value_objects import (
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunitySlug,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Community(AggregateRoot):
    organization_id: UUID
    slug: CommunitySlug
    name: CommunityName
    description: CommunityDescription | None = None
    visibility: CommunityVisibility = CommunityVisibility.PUBLIC
    created_by: UUID | None = None
    updated_by: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        slug: CommunitySlug,
        name: CommunityName,
        description: CommunityDescription | None = None,
        visibility: CommunityVisibility = CommunityVisibility.PUBLIC,
        created_by: UUID | None = None,
    ) -> "Community":
        community = cls(
            organization_id=organization_id,
            slug=slug,
            name=name,
            description=description,
            visibility=visibility,
            created_by=created_by,
            updated_by=created_by,
        )
        community.record_event(
            CommunityCreated(
                community_id=community.id,
                organization_id=organization_id,
                slug=str(slug),
                name=str(name),
            )
        )
        return community

    def update_profile(
        self,
        *,
        name: CommunityName | None = None,
        description: CommunityDescription | None = None,
        clear_description: bool = False,
        visibility: CommunityVisibility | None = None,
        updated_by: UUID | None = None,
    ) -> None:
        """`clear_description=True` is how a caller removes an existing
        description (distinct from `description=None`, which just means
        "no change" — the same "sentinel flag for explicit clearing"
        shape optional-field update methods across this codebase already
        use whenever `None` already means "leave unchanged")."""
        if name is not None:
            self.name = name
        if clear_description:
            self.description = None
        elif description is not None:
            self.description = description
        if visibility is not None:
            self.visibility = visibility
        if updated_by is not None:
            self.updated_by = updated_by

        self.touch()
        self.record_event(
            CommunityUpdated(community_id=self.id, organization_id=self.organization_id)
        )


@dataclass(kw_only=True, eq=False)
class CommunityMember(AggregateRoot):
    community_id: CommunityId
    user_id: UUID
    role: CommunityRole = CommunityRole.MEMBER
    status: CommunityMemberStatus = CommunityMemberStatus.ACTIVE
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        community_id: CommunityId,
        user_id: UUID,
        role: CommunityRole = CommunityRole.MEMBER,
        status: CommunityMemberStatus = CommunityMemberStatus.ACTIVE,
    ) -> "CommunityMember":
        """`role`/`status` default to `MEMBER`/`ACTIVE` — the only
        combination `JoinCommunityService` actually constructs today.
        Both parameters stay accepted (rather than hard-coded) so a
        future invitation/moderation module can construct an `INVITED`
        or `BLOCKED` member without this entity needing to change — see
        `CommunityMemberStatus`'s own docstring.
        """
        member = cls(community_id=community_id, user_id=user_id, role=role, status=status)
        if status is CommunityMemberStatus.ACTIVE:
            member.record_event(
                CommunityMemberJoined(
                    community_id=community_id.value, user_id=user_id, role=role.value
                )
            )
        return member

    def leave(self) -> None:
        self.status = CommunityMemberStatus.LEFT
        self.touch()
        self.record_event(
            CommunityMemberLeft(community_id=self.community_id.value, user_id=self.user_id)
        )

    def rejoin(self) -> None:
        """`LEFT` -> `ACTIVE` (rejoining) or `INVITED` -> `ACTIVE`
        (accepting an invitation) — both are mechanically identical
        (flip to `ACTIVE`, refresh `joined_at`), and both re-use the same
        row rather than creating a second one, so one method covers both
        — see `CommunityMemberRepository`'s own docstring for why
        `(community_id, user_id)` is a plain (non-partial) uniqueness
        constraint."""
        self.status = CommunityMemberStatus.ACTIVE
        self.joined_at = datetime.now(UTC)
        self.touch()
        self.record_event(
            CommunityMemberJoined(
                community_id=self.community_id.value, user_id=self.user_id, role=self.role.value
            )
        )
