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
    CommunityAppearanceUpdated,
    CommunityCategoryAssigned,
    CommunityCategoryCreated,
    CommunityCreated,
    CommunityFeaturedChanged,
    CommunityMemberJoined,
    CommunityMemberLeft,
    CommunityRuleCreated,
    CommunityRuleEnabledChanged,
    CommunityRuleUpdated,
    CommunityTagCreated,
    CommunityUpdated,
    CommunityVerifiedChanged,
)
from app.modules.community.domain.value_objects import (
    CommunityCategoryName,
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunityRuleTitle,
    CommunitySlug,
    CommunityTagName,
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
    category_id: UUID | None = None
    avatar_storage_path: str | None = None
    banner_storage_path: str | None = None
    is_verified: bool = False
    is_featured: bool = False

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
        category_id: UUID | None = None,
        clear_category: bool = False,
        updated_by: UUID | None = None,
    ) -> None:
        """`clear_description=True`/`clear_category=True` are how a
        caller removes an existing description/category assignment
        (distinct from `description=None`/`category_id=None`, which just
        mean "no change") — the same "sentinel flag for explicit
        clearing" shape optional-field update methods across this
        codebase already use whenever `None` already means "leave
        unchanged")."""
        if name is not None:
            self.name = name
        if clear_description:
            self.description = None
        elif description is not None:
            self.description = description
        if visibility is not None:
            self.visibility = visibility
        if clear_category:
            self.category_id = None
            self.record_event(CommunityCategoryAssigned(community_id=self.id, category_id=None))
        elif category_id is not None:
            self.category_id = category_id
            self.record_event(
                CommunityCategoryAssigned(community_id=self.id, category_id=category_id)
            )
        if updated_by is not None:
            self.updated_by = updated_by

        self.touch()
        self.record_event(
            CommunityUpdated(community_id=self.id, organization_id=self.organization_id)
        )

    def update_appearance(
        self,
        *,
        avatar_storage_path: str | None = None,
        clear_avatar: bool = False,
        banner_storage_path: str | None = None,
        clear_banner: bool = False,
    ) -> None:
        """`clear_avatar`/`clear_banner` remove an existing image
        (distinct from the corresponding `*_storage_path=None`, which
        means "no change") — the same clearing-sentinel shape
        `update_profile` already establishes."""
        if clear_avatar:
            self.avatar_storage_path = None
        elif avatar_storage_path is not None:
            self.avatar_storage_path = avatar_storage_path
        if clear_banner:
            self.banner_storage_path = None
        elif banner_storage_path is not None:
            self.banner_storage_path = banner_storage_path

        self.touch()
        self.record_event(CommunityAppearanceUpdated(community_id=self.id))

    def set_verified(self, value: bool) -> None:
        """Platform-level trust signal — set by a caller holding the
        `communities.verify` RBAC permission, not a community's own
        `OWNER`/`ADMIN` (see `FeatureCommunitiesService`'s own
        docstring for why this is authorized differently from
        `update_profile`)."""
        if self.is_verified is value:
            return
        self.is_verified = value
        self.touch()
        self.record_event(CommunityVerifiedChanged(community_id=self.id, is_verified=value))

    def set_featured(self, value: bool) -> None:
        """Platform-level curation flag — see `set_verified`'s own
        docstring for the identical authorization reasoning."""
        if self.is_featured is value:
            return
        self.is_featured = value
        self.touch()
        self.record_event(CommunityFeaturedChanged(community_id=self.id, is_featured=value))


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


@dataclass(kw_only=True, eq=False)
class CommunityCategory(AggregateRoot):
    """A platform-wide, admin-manageable vocabulary entry (Cardiology,
    Dermatology, ...) — a real table rather than a closed `StrEnum` so
    new categories can be added without a code deploy, per this task's
    own "Categories must be extensible" requirement. The same
    "extensible vocabulary as its own aggregate" shape
    `app.modules.authentication.domain.entities.Permission` already
    establishes for its own, analogous need.
    """

    name: CommunityCategoryName
    slug: CommunitySlug
    description: str | None = None
    is_active: bool = True

    @classmethod
    def create(
        cls, *, name: CommunityCategoryName, slug: CommunitySlug, description: str | None = None
    ) -> "CommunityCategory":
        category = cls(name=name, slug=slug, description=description)
        category.record_event(CommunityCategoryCreated(category_id=category.id, name=str(name)))
        return category

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        self.is_active = True
        self.touch()


@dataclass(kw_only=True, eq=False)
class CommunityTag(AggregateRoot):
    """A reusable, searchable medical tag — shared across every
    community that assigns it (the assignment itself is a plain
    `community_tags` join row, not a rich entity — see
    `CommunityTagRepository`'s own docstring)."""

    name: CommunityTagName

    @classmethod
    def create(cls, *, name: CommunityTagName) -> "CommunityTag":
        tag = cls(name=name)
        tag.record_event(CommunityTagCreated(tag_id=tag.id, name=str(name)))
        return tag


@dataclass(kw_only=True, eq=False)
class CommunityRule(AggregateRoot):
    community_id: CommunityId
    title: CommunityRuleTitle
    description: str | None = None
    position: int = 0
    is_enabled: bool = True

    @classmethod
    def create(
        cls,
        *,
        community_id: CommunityId,
        title: CommunityRuleTitle,
        description: str | None = None,
        position: int = 0,
    ) -> "CommunityRule":
        rule = cls(
            community_id=community_id, title=title, description=description, position=position
        )
        rule.record_event(
            CommunityRuleCreated(rule_id=rule.id, community_id=community_id.value, title=str(title))
        )
        return rule

    def update_details(
        self, *, title: CommunityRuleTitle | None = None, description: str | None = None
    ) -> None:
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        self.touch()
        self.record_event(
            CommunityRuleUpdated(rule_id=self.id, community_id=self.community_id.value)
        )

    def set_enabled(self, value: bool) -> None:
        if self.is_enabled is value:
            return
        self.is_enabled = value
        self.touch()
        self.record_event(
            CommunityRuleEnabledChanged(
                rule_id=self.id, community_id=self.community_id.value, is_enabled=value
            )
        )

    def reposition(self, position: int) -> None:
        self.position = position
        self.touch()
