"""Data Transfer Objects for the Community module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape `app.modules.organization.application.dto` already establishes;
`CommunitySummaryDTO`/`CommunityMemberSummaryDTO` are also re-exported
from `public/dto.py` for other modules to depend on.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)

# --- CreateCommunity -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateCommunityInput:
    organization_id: UUID
    slug: str
    name: str
    created_by: UUID
    description: str | None = None
    visibility: CommunityVisibility = CommunityVisibility.PUBLIC


@dataclass(frozen=True, slots=True)
class CreateCommunityOutput:
    community_id: UUID
    organization_id: UUID
    slug: str
    name: str
    visibility: CommunityVisibility


# --- UpdateCommunity ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateCommunityInput:
    community_id: UUID
    acting_user_id: UUID
    name: str | None = None
    description: str | None = None
    clear_description: bool = False
    visibility: CommunityVisibility | None = None
    category_id: UUID | None = None
    clear_category: bool = False


@dataclass(frozen=True, slots=True)
class UpdateCommunityOutput:
    community_id: UUID
    name: str
    visibility: CommunityVisibility


# --- DeleteCommunity ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DeleteCommunityInput:
    community_id: UUID
    acting_user_id: UUID


# --- JoinCommunity / LeaveCommunity ------------------------------------------


@dataclass(frozen=True, slots=True)
class JoinCommunityInput:
    community_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class JoinCommunityOutput:
    member_id: UUID
    community_id: UUID
    user_id: UUID
    role: CommunityRole
    status: CommunityMemberStatus
    joined_at: datetime


@dataclass(frozen=True, slots=True)
class LeaveCommunityInput:
    community_id: UUID
    user_id: UUID


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class CommunitySummaryDTO:
    community_id: UUID
    organization_id: UUID
    slug: str
    name: str
    visibility: CommunityVisibility
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    created_by: UUID | None = None
    category_id: UUID | None = None
    avatar_storage_path: str | None = None
    banner_storage_path: str | None = None
    is_verified: bool = False
    is_featured: bool = False

    @property
    def id(self) -> UUID:
        """Alias for `community_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.community_id


@dataclass(frozen=True, slots=True)
class CommunityMemberSummaryDTO:
    member_id: UUID
    community_id: UUID
    user_id: UUID
    role: CommunityRole
    status: CommunityMemberStatus
    joined_at: datetime

    @property
    def id(self) -> UUID:
        """Alias for `member_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.member_id


# --- ListCommunities ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ListCommunitiesOutput:
    items: tuple[CommunitySummaryDTO, ...]
    total: int


# --- BrowseCommunities / SearchCommunities -----------------------------------


@dataclass(frozen=True, slots=True)
class BrowseCommunitiesInput:
    organization_id: UUID
    category_id: UUID | None = None
    tag_ids: tuple[UUID, ...] = ()
    visibilities: tuple[CommunityVisibility, ...] | None = None
    sort: str = "recent"  # "recent" | "popular" | "alphabetical"
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class BrowseCommunitiesOutput:
    items: tuple[CommunitySummaryDTO, ...]
    total: int


@dataclass(frozen=True, slots=True)
class SearchCommunitiesInput:
    organization_id: UUID
    query: str
    category_id: UUID | None = None
    tag_ids: tuple[UUID, ...] = ()
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SearchCommunitiesOutput:
    items: tuple[CommunitySummaryDTO, ...]
    total: int


# --- FeatureCommunities (featured/verified curation) -------------------------


@dataclass(frozen=True, slots=True)
class ListFeaturedCommunitiesInput:
    organization_id: UUID
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SetCommunityFeaturedInput:
    community_id: UUID
    featured: bool


@dataclass(frozen=True, slots=True)
class SetCommunityVerifiedInput:
    community_id: UUID
    verified: bool


# --- UpdateCommunityAppearance ------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateCommunityAppearanceInput:
    community_id: UUID
    acting_user_id: UUID
    avatar_data: bytes | None = None
    avatar_content_type: str | None = None
    avatar_filename: str | None = None
    clear_avatar: bool = False
    banner_data: bytes | None = None
    banner_content_type: str | None = None
    banner_filename: str | None = None
    clear_banner: bool = False


@dataclass(frozen=True, slots=True)
class UpdateCommunityAppearanceOutput:
    community_id: UUID
    avatar_storage_path: str | None
    banner_storage_path: str | None


# --- Community categories -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommunityCategorySummaryDTO:
    category_id: UUID
    name: str
    slug: str
    is_active: bool
    description: str | None = None

    @property
    def id(self) -> UUID:
        """Alias for `category_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.category_id


@dataclass(frozen=True, slots=True)
class CreateCommunityCategoryInput:
    name: str
    slug: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CreateCommunityCategoryOutput:
    category_id: UUID
    name: str
    slug: str


# --- Community tags ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommunityTagSummaryDTO:
    tag_id: UUID
    name: str

    @property
    def id(self) -> UUID:
        """Alias for `tag_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.tag_id


@dataclass(frozen=True, slots=True)
class AssignCommunityTagInput:
    community_id: UUID
    acting_user_id: UUID
    tag_name: str


@dataclass(frozen=True, slots=True)
class UnassignCommunityTagInput:
    community_id: UUID
    acting_user_id: UUID
    tag_id: UUID


@dataclass(frozen=True, slots=True)
class SearchCommunityTagsInput:
    query: str
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SearchCommunityTagsOutput:
    items: tuple[CommunityTagSummaryDTO, ...]
    total: int


# --- Community rules -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommunityRuleSummaryDTO:
    rule_id: UUID
    community_id: UUID
    title: str
    position: int
    is_enabled: bool
    description: str | None = None

    @property
    def id(self) -> UUID:
        """Alias for `rule_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.rule_id


@dataclass(frozen=True, slots=True)
class CreateCommunityRuleInput:
    community_id: UUID
    acting_user_id: UUID
    title: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CreateCommunityRuleOutput:
    rule_id: UUID
    community_id: UUID
    title: str
    position: int


@dataclass(frozen=True, slots=True)
class UpdateCommunityRuleInput:
    rule_id: UUID
    community_id: UUID
    acting_user_id: UUID
    title: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class SetCommunityRuleEnabledInput:
    rule_id: UUID
    community_id: UUID
    acting_user_id: UUID
    enabled: bool


@dataclass(frozen=True, slots=True)
class DeleteCommunityRuleInput:
    rule_id: UUID
    community_id: UUID
    acting_user_id: UUID


@dataclass(frozen=True, slots=True)
class ReorderCommunityRulesInput:
    community_id: UUID
    acting_user_id: UUID
    ordered_rule_ids: Sequence[UUID] = field(default_factory=tuple)


# --- Community statistics -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommunityStatisticsDTO:
    community_id: UUID
    member_count: int
    moderator_count: int
    rule_count: int
    tag_count: int
    is_verified: bool
    is_featured: bool
    created_at: datetime
