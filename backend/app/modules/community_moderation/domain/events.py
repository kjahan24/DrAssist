"""Domain events for the Community Moderation module. All
`@dataclass(frozen=True, kw_only=True)` subclasses of `DomainEvent` — see
that base class's own docstring."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_moderation.domain.enums import (
    ModerationRestrictionType,
    ModerationTargetType,
    ReportPriority,
    ReportReason,
)
from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ReportCreated(DomainEvent):
    report_id: UUID
    reporter_id: UUID
    target_type: ModerationTargetType
    target_id: UUID
    reason: ReportReason
    priority: ReportPriority


@dataclass(frozen=True, kw_only=True)
class ReportAssigned(DomainEvent):
    report_id: UUID
    moderator_id: UUID


@dataclass(frozen=True, kw_only=True)
class ReportResolved(DomainEvent):
    report_id: UUID
    moderator_id: UUID
    resolution: str


@dataclass(frozen=True, kw_only=True)
class ReportRejected(DomainEvent):
    report_id: UUID
    moderator_id: UUID
    resolution: str


@dataclass(frozen=True, kw_only=True)
class ReportPriorityChanged(DomainEvent):
    report_id: UUID
    moderator_id: UUID
    previous_priority: ReportPriority
    new_priority: ReportPriority


@dataclass(frozen=True, kw_only=True)
class DoctorVerificationRequested(DomainEvent):
    verification_id: UUID
    doctor_id: UUID
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorVerificationApproved(DomainEvent):
    verification_id: UUID
    doctor_id: UUID
    verifier_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorVerificationRejected(DomainEvent):
    verification_id: UUID
    doctor_id: UUID
    verifier_id: UUID
    reason: str


@dataclass(frozen=True, kw_only=True)
class DoctorVerificationRevoked(DomainEvent):
    verification_id: UUID
    doctor_id: UUID
    verifier_id: UUID
    reason: str


@dataclass(frozen=True, kw_only=True)
class ModerationRestrictionIssued(DomainEvent):
    restriction_id: UUID
    user_id: UUID
    community_id: UUID
    restriction_type: ModerationRestrictionType
    issued_by: UUID
