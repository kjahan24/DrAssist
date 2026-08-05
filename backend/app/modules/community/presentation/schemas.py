"""Pydantic v2 request/response schemas for the Community module.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `created_by`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.schemas.base import ORJSONModel

_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class CommunityResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    slug: str
    name: str
    description: str | None = None
    visibility: CommunityVisibility
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    category_id: UUID | None = None
    avatar_storage_path: str | None = None
    banner_storage_path: str | None = None
    is_verified: bool = False
    is_featured: bool = False


class CommunityMemberResponse(ORJSONModel):
    id: UUID
    community_id: UUID
    user_id: UUID
    role: CommunityRole
    status: CommunityMemberStatus
    joined_at: datetime


class CreateCommunityRequest(ORJSONModel):
    slug: str = Field(min_length=3, max_length=64, pattern=_SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    visibility: CommunityVisibility = CommunityVisibility.PUBLIC


class UpdateCommunityRequest(ORJSONModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    clear_description: bool = False
    visibility: CommunityVisibility | None = None
    category_id: UUID | None = None
    clear_category: bool = False


# --- Discovery (browse/search/featured) --------------------------------------


class CommunitySearchResponse(ORJSONModel):
    items: list[CommunityResponse]
    total: int


class SetCommunityFeaturedRequest(ORJSONModel):
    featured: bool


class SetCommunityVerifiedRequest(ORJSONModel):
    verified: bool


# --- Categories ----------------------------------------------------------------


class CommunityCategoryResponse(ORJSONModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    description: str | None = None


class CreateCommunityCategoryRequest(ORJSONModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=3, max_length=64, pattern=_SLUG_PATTERN)
    description: str | None = Field(default=None, max_length=1000)


# --- Tags ------------------------------------------------------------------------


class CommunityTagResponse(ORJSONModel):
    id: UUID
    name: str


class AssignCommunityTagRequest(ORJSONModel):
    tag_name: str = Field(min_length=1, max_length=50)


class CommunityTagSearchResponse(ORJSONModel):
    items: list[CommunityTagResponse]
    total: int


# --- Rules -------------------------------------------------------------------------


class CommunityRuleResponse(ORJSONModel):
    id: UUID
    community_id: UUID
    title: str
    position: int
    is_enabled: bool
    description: str | None = None


class CreateCommunityRuleRequest(ORJSONModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class UpdateCommunityRuleRequest(ORJSONModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class SetCommunityRuleEnabledRequest(ORJSONModel):
    enabled: bool


class ReorderCommunityRulesRequest(ORJSONModel):
    ordered_rule_ids: list[UUID]


# --- Statistics -------------------------------------------------------------------


class CommunityStatisticsResponse(ORJSONModel):
    community_id: UUID
    member_count: int
    moderator_count: int
    rule_count: int
    tag_count: int
    is_verified: bool
    is_featured: bool
    created_at: datetime
