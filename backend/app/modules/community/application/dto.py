"""Data Transfer Objects for the Community module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape `app.modules.organization.application.dto` already establishes;
`CommunitySummaryDTO`/`CommunityMemberSummaryDTO` are also re-exported
from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
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
