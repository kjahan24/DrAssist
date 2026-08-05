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
