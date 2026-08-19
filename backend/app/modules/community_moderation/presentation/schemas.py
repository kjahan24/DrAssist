"""Pydantic v2 response schemas for the Community Moderation module's
REST API. Every schema here mirrors an application-layer summary DTO
one-to-one via `model_validate`, the same "response schema, not a domain
type" split every prior module's own `presentation/schemas.py`
establishes. Request bodies are plain Pydantic models too — unlike
`community_engagement` (no free-text fields anywhere in that module),
this module's mutating endpoints (report descriptions, moderation
reasons, resolutions) genuinely need body validation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
    VerificationStatus,
)

# --- Requests ------------------------------------------------------------------------


class CreateReportRequest(BaseModel):
    community_id: UUID
    target_type: ModerationTargetType
    target_id: UUID
    reason: ReportReason
    description: str | None = Field(default=None, max_length=2000)


class AssignReportRequest(BaseModel):
    community_id: UUID
    note: str | None = Field(default=None, max_length=2000)


class ResolveReportRequest(BaseModel):
    community_id: UUID
    resolution: str = Field(min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)


class RejectReportRequest(BaseModel):
    community_id: UUID
    resolution: str = Field(min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)


class CreateModerationActionRequest(BaseModel):
    action_type: ModerationActionType
    target_type: ModerationTargetType
    target_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    report_id: UUID | None = None
    moderator_note: str | None = Field(default=None, max_length=2000)


class ContentModerationRequest(BaseModel):
    target_type: ModerationTargetType
    target_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    report_id: UUID | None = None
    moderator_note: str | None = Field(default=None, max_length=2000)


class WarnUserRequest(BaseModel):
    community_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    report_id: UUID | None = None


class RestrictUserRequest(BaseModel):
    community_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    duration_days: int = Field(gt=0, le=3650)
    report_id: UUID | None = None


class SuspendUserRequest(BaseModel):
    community_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    duration_days: int | None = Field(default=None, gt=0, le=3650)
    report_id: UUID | None = None


class RequestDoctorVerificationRequest(BaseModel):
    specialty: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] | None = None


class ApproveDoctorVerificationRequest(BaseModel):
    specialty: str | None = Field(default=None, max_length=200)


class RejectDoctorVerificationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class RevokeDoctorVerificationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


# --- Responses -----------------------------------------------------------------------


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    community_id: UUID
    reporter_id: UUID
    target_type: ModerationTargetType
    target_id: UUID
    reason: ReportReason
    status: ReportStatus
    priority: ReportPriority
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    assigned_moderator_id: UUID | None = None
    moderator_note: str | None = None
    resolution: str | None = None
    resolved_at: datetime | None = None


class ReportFeedResponse(BaseModel):
    items: list[ReportResponse]
    next_cursor: str | None = None


class ModerationActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    actor_id: UUID
    action_type: ModerationActionType
    target_type: ModerationTargetType
    target_id: UUID
    reason: str
    created_at: datetime
    report_id: UUID | None = None
    moderator_note: str | None = None
    previous_state: str | None = None
    new_state: str | None = None


class RestrictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    community_id: UUID
    user_id: UUID
    issued_by: UUID
    restriction_type: ModerationRestrictionType
    reason: str
    starts_at: datetime
    created_at: datetime
    ends_at: datetime | None = None
    report_id: UUID | None = None


class ModerationStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    community_id: UUID | None
    current_restriction_type: ModerationRestrictionType | None
    restricted_until: datetime | None
    active_restriction_count: int
    is_restricted: bool


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doctor_id: UUID
    user_id: UUID
    organization_id: UUID
    status: VerificationStatus
    created_at: datetime
    updated_at: datetime
    specialty: str | None = None
    verifier_id: UUID | None = None
    verified_at: datetime | None = None
    rejection_reason: str | None = None
    revocation_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
