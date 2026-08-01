"""Pydantic v2 request/response schemas for the Family / Caregiver Access
module.

Schemas never expose a domain entity directly, and never accept
server-controlled fields (`id`, `organization_id`, `status`,
`invitation_token`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `InviteCaregiverResponse` is the one schema that *does*
carry `invitation_token` — the raw value, returned exactly once, on the
one response where it is ever produced (see
`application/dto.py::InviteCaregiverOutput`'s own docstring);
`FamilyAccessResponse` never includes it, not even the hash.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.family_access.domain.enums import AccessLevel, FamilyAccessStatus, Relationship
from app.schemas.base import ORJSONModel


class FamilyAccessResponse(ORJSONModel):
    id: UUID
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


class InviteCaregiverRequest(ORJSONModel):
    patient_id: UUID
    caregiver_user_id: UUID
    relationship: Relationship
    access_level: AccessLevel
    notes: str | None = Field(default=None, max_length=1000)


class InviteCaregiverResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    caregiver_user_id: UUID
    status: FamilyAccessStatus
    invitation_token: str
    invitation_expires_at: datetime
