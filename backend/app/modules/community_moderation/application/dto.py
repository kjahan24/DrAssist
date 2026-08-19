"""Application-layer DTOs for the Community Moderation module.

Input DTOs carry an explicit `organization_id`/`acting_*_id` field for the
same reason `app.modules.community_engagement.application.dto`'s own Input
DTOs do: this module has no community-membership-style "get it for free"
tenant check the way content-creation modules do, so tenant comparison is
threaded through explicitly wherever a target is resolved. See
`_target_resolution.py`'s own docstring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
    VerificationStatus,
)
from app.modules.community_moderation.domain.value_objects import UserModerationStatus

# --- Reports -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateReportInput:
    organization_id: UUID
    community_id: UUID
    reporter_id: UUID
    target_type: ModerationTargetType
    target_id: UUID
    reason: ReportReason
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ReportSummaryDTO:
    report_id: UUID
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

    @property
    def id(self) -> UUID:
        return self.report_id


@dataclass(frozen=True, slots=True)
class ListReportsInput:
    organization_id: UUID
    community_id: UUID | None = None
    status: ReportStatus | None = None
    priority: ReportPriority | None = None
    assigned_moderator_id: UUID | None = None
    cursor: str | None = None
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ReportFeedOutput:
    items: list[ReportSummaryDTO]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class AssignReportInput:
    report_id: UUID
    moderator_id: UUID
    community_id: UUID
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ResolveReportInput:
    report_id: UUID
    moderator_id: UUID
    community_id: UUID
    resolution: str
    note: str | None = None


@dataclass(frozen=True, slots=True)
class RejectReportInput:
    report_id: UUID
    moderator_id: UUID
    community_id: UUID
    resolution: str
    note: str | None = None


# --- Moderation actions --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModerationActionSummaryDTO:
    action_id: UUID
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

    @property
    def id(self) -> UUID:
        return self.action_id


@dataclass(frozen=True, slots=True)
class CreateModerationActionInput:
    organization_id: UUID
    actor_id: UUID
    action_type: ModerationActionType
    target_type: ModerationTargetType
    target_id: UUID
    reason: str
    report_id: UUID | None = None
    moderator_note: str | None = None


@dataclass(frozen=True, slots=True)
class ContentModerationInput:
    """Shared shape for `ReviewContent`/`RemoveContent`/`RestoreContent`/
    `LockContent` — each service supplies its own fixed
    `ModerationActionType`, so this input never carries one itself."""

    organization_id: UUID
    actor_id: UUID
    target_type: ModerationTargetType
    target_id: UUID
    reason: str
    report_id: UUID | None = None
    moderator_note: str | None = None


# --- User restrictions ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RestrictionSummaryDTO:
    restriction_id: UUID
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

    @property
    def id(self) -> UUID:
        return self.restriction_id


@dataclass(frozen=True, slots=True)
class WarnUserInput:
    organization_id: UUID
    community_id: UUID
    moderator_id: UUID
    user_id: UUID
    reason: str
    report_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RestrictUserInput:
    organization_id: UUID
    community_id: UUID
    moderator_id: UUID
    user_id: UUID
    reason: str
    duration_days: int
    report_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class SuspendUserInput:
    organization_id: UUID
    community_id: UUID
    moderator_id: UUID
    user_id: UUID
    reason: str
    # `None` means permanent — a "Permanent ban where authorized" request,
    # gated by a stricter admin-rank check than a time-bounded suspension.
    # See `SuspendUserService`'s own docstring.
    duration_days: int | None = None
    report_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GetModerationStatusInput:
    user_id: UUID
    community_id: UUID | None = None


# --- Doctor verification --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerificationSummaryDTO:
    verification_id: UUID
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
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> UUID:
        return self.verification_id


@dataclass(frozen=True, slots=True)
class RequestDoctorVerificationInput:
    doctor_id: UUID
    requesting_user_id: UUID
    specialty: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ApproveDoctorVerificationInput:
    verification_id: UUID
    verifier_id: UUID
    specialty: str | None = None


@dataclass(frozen=True, slots=True)
class RejectDoctorVerificationInput:
    verification_id: UUID
    verifier_id: UUID
    reason: str


@dataclass(frozen=True, slots=True)
class RevokeDoctorVerificationInput:
    verification_id: UUID
    verifier_id: UUID
    reason: str


__all__ = [
    "ApproveDoctorVerificationInput",
    "AssignReportInput",
    "ContentModerationInput",
    "CreateModerationActionInput",
    "CreateReportInput",
    "GetModerationStatusInput",
    "ListReportsInput",
    "ModerationActionSummaryDTO",
    "RejectDoctorVerificationInput",
    "RejectReportInput",
    "ReportFeedOutput",
    "ReportSummaryDTO",
    "RequestDoctorVerificationInput",
    "ResolveReportInput",
    "RestrictUserInput",
    "RestrictionSummaryDTO",
    "RevokeDoctorVerificationInput",
    "SuspendUserInput",
    "UserModerationStatus",
    "VerificationSummaryDTO",
    "WarnUserInput",
]
