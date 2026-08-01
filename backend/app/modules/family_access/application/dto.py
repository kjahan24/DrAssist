"""Data Transfer Objects for the Family / Caregiver Access module's
application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`). Use-case input/output DTOs are plain,
immutable dataclasses; `FamilyAccessSummaryDTO` is also re-exported from
`public/dto.py` for other modules to depend on.

`InviteCaregiverOutput.invitation_token` is the one place the *raw*
invitation token ever appears — see `domain/entities.py`'s own module
docstring for why it is never persisted and therefore can never be
re-read later. `FamilyAccessSummaryDTO` deliberately carries no token
field at all (not even the hash): no consumer needs it — the raw token
is already handed back exactly once above, and looking an invitation up
*by* its token is `GetInvitation`'s job (see
`application/services/family_access_query_service.py`), not something a
generic summary read model needs to expose.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.family_access.domain.enums import AccessLevel, FamilyAccessStatus, Relationship

# --- InviteCaregiver --------------------------------------------------


@dataclass(frozen=True, slots=True)
class InviteCaregiverInput:
    patient_id: UUID
    caregiver_user_id: UUID
    relationship: Relationship
    access_level: AccessLevel
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class InviteCaregiverOutput:
    family_access_id: UUID
    organization_id: UUID
    patient_id: UUID
    caregiver_user_id: UUID
    status: FamilyAccessStatus
    invitation_token: str
    invitation_expires_at: datetime


# --- AcceptInvitation / RejectInvitation / RevokeAccess --------------------


@dataclass(frozen=True, slots=True)
class AcceptInvitationInput:
    family_access_id: UUID


@dataclass(frozen=True, slots=True)
class RejectInvitationInput:
    family_access_id: UUID


@dataclass(frozen=True, slots=True)
class RevokeAccessInput:
    family_access_id: UUID


@dataclass(frozen=True, slots=True)
class FamilyAccessStatusOutput:
    family_access_id: UUID
    status: FamilyAccessStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class FamilyAccessSummaryDTO:
    family_access_id: UUID
    organization_id: UUID
    patient_id: UUID
    caregiver_user_id: UUID
    relationship: Relationship
    access_level: AccessLevel
    status: FamilyAccessStatus
    invitation_expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    notes: str | None = None

    @property
    def id(self) -> UUID:
        """Alias for `family_access_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.family_access_id
