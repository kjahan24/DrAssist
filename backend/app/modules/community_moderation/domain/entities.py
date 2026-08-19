"""Community Moderation module aggregates/entities: `CommunityReport`,
`ModerationAction`, `ModerationRestriction`, `DoctorVerification`.

`ModerationAction` extends `Entity`, not `AggregateRoot` — it has no
mutation method beyond its own `record()` factory, no `updated_at`, and
raises no domain event of its own (it *is* the record of something that
already happened), mirroring `app.modules.audit_log.domain.entities
.AuditLog` exactly, for the identical reason: "Never delete audit history
through normal APIs" (this task's own AUDIT section) is trivially true of
a type with no delete/update method at all, at either the domain or
repository layer — see `repositories.py`'s own docstring.

There is deliberately no separate "current content moderation status"
aggregate (e.g. a `ContentModerationRecord` keyed by
`(target_type, target_id)`). `ReviewContent`/`RemoveContent`/
`RestoreContent`/`LockContent` each simply record one more
`ModerationAction` row; "the current moderation status of content X" is
computed live as "the `new_state` of the most recent `ModerationAction`
row for that target" (or `ContentModerationStatus.ACTIVE` if none exists)
by `GetModerationStatusService`/`ModerationActionRepository
.get_latest_for_target` — the same "compute live, never denormalize"
choice `app.modules.community_engagement` already made for vote counts,
applied here to avoid a second, independently-mutable source of truth
that could drift from the audit trail itself.

**Scope boundary, disclosed deliberately**: none of these entities mutate
`community_posts`/`community_questions`/`community_answers`/
`community_comments`' own domain entities or database rows. A `REMOVE`
action recorded here does not, by itself, hide the underlying post from
that module's own feed/search — wiring each content module's own read
path to consult this module's moderation status is a future integration,
exactly parallel to how this task's own PROMPT excludes "external
medical-license verification APIs" from `DoctorVerification` and asks for
"an extensible verification abstraction for future integration" instead.
Building deeper coupling now would require adding command methods to four
already-complete modules' public ports (none of which expose any today —
see each module's own `public/interfaces.py`), inventing status values
those modules' own `PostStatus`/`QuestionStatus`/`AnswerStatus`/
`CommentStatus` enums do not have (no module has a `LOCKED`/`REMOVED`
status distinct from author-initiated `ARCHIVED`/`DELETED`), and — for
posts specifically — a `restore()` domain method and `is_locked`
equivalents that do not exist for questions/answers/comments today. None
of that is "absolutely necessary" to satisfy this module's own literal
requirements (a working, auditable report/action/restriction/verification
system), so none of it was done.

`ModerationRestriction` is always community-scoped (`community_id` is
required, not nullable) — "community moderation" naturally scopes to a
community, and this codebase has no platform-wide `is_admin`/`UserRole`
concept to hang an unscoped restriction off of (confirmed: no such enum
exists anywhere in `app.modules.authentication`). Authorization for
issuing one reuses the exact `CommunityRole` rank hierarchy every content
module's own `_authorization.py` already established — see this module's
own `application/services/_authorization.py`.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
from app.modules.community_moderation.domain.events import (
    DoctorVerificationApproved,
    DoctorVerificationRejected,
    DoctorVerificationRequested,
    DoctorVerificationRevoked,
    ModerationRestrictionIssued,
    ReportAssigned,
    ReportCreated,
    ReportPriorityChanged,
    ReportRejected,
    ReportResolved,
)
from app.modules.community_moderation.domain.exceptions import (
    DoctorVerificationCannotBeResubmittedError,
    DoctorVerificationNotPendingError,
    DoctorVerificationNotVerifiedError,
    ModerationReasonRequiredError,
    ReportAlreadyClosedError,
)
from app.shared.domain.entity import AggregateRoot, Entity

_HIGH_PRIORITY_REASONS = frozenset(
    {
        ReportReason.DANGEROUS_MEDICAL_ADVICE,
        ReportReason.SELF_HARM_CONCERN,
        ReportReason.ILLEGAL_CONTENT,
    }
)
_LOW_PRIORITY_REASONS = frozenset({ReportReason.SPAM, ReportReason.OTHER})

_OPEN_STATUSES = (ReportStatus.OPEN, ReportStatus.UNDER_REVIEW)


def _default_priority_for_reason(reason: ReportReason) -> ReportPriority:
    """Reporters never choose their own priority (a self-serve "mark this
    CRITICAL" option would itself be a spam/abuse vector) — priority is
    derived deterministically from `reason`, with `set_priority()`
    available for a moderator to re-triage afterward."""
    if reason in _HIGH_PRIORITY_REASONS:
        return ReportPriority.HIGH
    if reason in _LOW_PRIORITY_REASONS:
        return ReportPriority.LOW
    return ReportPriority.MEDIUM


@dataclass(kw_only=True, eq=False)
class CommunityReport(AggregateRoot):
    organization_id: UUID
    community_id: UUID
    reporter_id: UUID
    target_type: ModerationTargetType
    target_id: UUID
    reason: ReportReason
    status: ReportStatus = ReportStatus.OPEN
    priority: ReportPriority = ReportPriority.MEDIUM
    description: str | None = None
    assigned_moderator_id: UUID | None = None
    moderator_note: str | None = None
    resolution: str | None = None
    resolved_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        community_id: UUID,
        reporter_id: UUID,
        target_type: ModerationTargetType,
        target_id: UUID,
        reason: ReportReason,
        description: str | None = None,
    ) -> "CommunityReport":
        priority = _default_priority_for_reason(reason)
        report = cls(
            organization_id=organization_id,
            community_id=community_id,
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            priority=priority,
            description=description,
        )
        report.record_event(
            ReportCreated(
                report_id=report.id,
                reporter_id=reporter_id,
                target_type=target_type,
                target_id=target_id,
                reason=reason,
                priority=priority,
            )
        )
        return report

    def _ensure_open(self) -> None:
        if self.status not in _OPEN_STATUSES:
            raise ReportAlreadyClosedError(self.id)

    def assign(self, *, moderator_id: UUID, note: str | None = None) -> None:
        self._ensure_open()
        self.status = ReportStatus.UNDER_REVIEW
        self.assigned_moderator_id = moderator_id
        if note is not None:
            self.moderator_note = note
        self.touch()
        self.record_event(ReportAssigned(report_id=self.id, moderator_id=moderator_id))

    def resolve(self, *, moderator_id: UUID, resolution: str, note: str | None = None) -> None:
        self._ensure_open()
        self.status = ReportStatus.RESOLVED
        self.assigned_moderator_id = moderator_id
        self.resolution = resolution
        if note is not None:
            self.moderator_note = note
        self.resolved_at = datetime.now(UTC)
        self.touch()
        self.record_event(
            ReportResolved(report_id=self.id, moderator_id=moderator_id, resolution=resolution)
        )

    def reject(self, *, moderator_id: UUID, resolution: str, note: str | None = None) -> None:
        self._ensure_open()
        self.status = ReportStatus.REJECTED
        self.assigned_moderator_id = moderator_id
        self.resolution = resolution
        if note is not None:
            self.moderator_note = note
        self.resolved_at = datetime.now(UTC)
        self.touch()
        self.record_event(
            ReportRejected(report_id=self.id, moderator_id=moderator_id, resolution=resolution)
        )

    def set_priority(self, priority: ReportPriority, *, moderator_id: UUID) -> None:
        self._ensure_open()
        previous_priority = self.priority
        self.priority = priority
        self.touch()
        self.record_event(
            ReportPriorityChanged(
                report_id=self.id,
                moderator_id=moderator_id,
                previous_priority=previous_priority,
                new_priority=priority,
            )
        )


@dataclass(kw_only=True, eq=False)
class ModerationAction(Entity):
    organization_id: UUID
    actor_id: UUID
    action_type: ModerationActionType
    target_type: ModerationTargetType
    target_id: UUID
    reason: str
    report_id: UUID | None = None
    moderator_note: str | None = None
    previous_state: str | None = None
    new_state: str | None = None
    # Not the persisted source of truth — see `AuditLog`'s own identical
    # field, whose docstring explains why: the database's
    # `server_default=func.now()` (via `CreatedAtMixin`) always overwrites
    # this on round-trip; it only gives a freshly `record()`-ed, not-yet-
    # persisted entity a usable in-memory value.
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            raise ModerationReasonRequiredError()
        self.reason = self.reason.strip()

    @classmethod
    def record(
        cls,
        *,
        organization_id: UUID,
        actor_id: UUID,
        action_type: ModerationActionType,
        target_type: ModerationTargetType,
        target_id: UUID,
        reason: str,
        report_id: UUID | None = None,
        moderator_note: str | None = None,
        previous_state: str | None = None,
        new_state: str | None = None,
    ) -> "ModerationAction":
        """Named `record()`, not `create()` — mirrors `AuditLog.record()`'s
        own naming reasoning: this module's own `ModerationActionType
        .APPROVE`/etc. would make `.create()` read as "record a Create
        action" specifically, when this factory is used for every action
        type."""
        return cls(
            organization_id=organization_id,
            actor_id=actor_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            report_id=report_id,
            moderator_note=moderator_note,
            previous_state=previous_state,
            new_state=new_state,
        )


@dataclass(kw_only=True, eq=False)
class ModerationRestriction(AggregateRoot):
    """No mutation method beyond `issue()` — a restriction, once issued,
    is a historical fact; nothing in this task's own APPLICATION section
    names an "unrestrict"/"lift" use case (only `RestrictUser`/
    `SuspendUser`/`WarnUser`), so none is built. A temporary restriction's
    "activeness" is instead a pure computed check (`is_active()`) against
    `ends_at`, never a stored, independently-mutable flag — the same
    "compute live" reasoning as `ModerationAction`'s own module docstring.
    """

    organization_id: UUID
    community_id: UUID
    user_id: UUID
    issued_by: UUID
    restriction_type: ModerationRestrictionType
    reason: str
    starts_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ends_at: datetime | None = None
    report_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            raise ModerationReasonRequiredError()
        self.reason = self.reason.strip()

    @classmethod
    def issue(
        cls,
        *,
        organization_id: UUID,
        community_id: UUID,
        user_id: UUID,
        issued_by: UUID,
        restriction_type: ModerationRestrictionType,
        reason: str,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        report_id: UUID | None = None,
    ) -> "ModerationRestriction":
        restriction = cls(
            organization_id=organization_id,
            community_id=community_id,
            user_id=user_id,
            issued_by=issued_by,
            restriction_type=restriction_type,
            reason=reason,
            starts_at=starts_at if starts_at is not None else datetime.now(UTC),
            ends_at=ends_at,
            report_id=report_id,
        )
        restriction.record_event(
            ModerationRestrictionIssued(
                restriction_id=restriction.id,
                user_id=user_id,
                community_id=community_id,
                restriction_type=restriction_type,
                issued_by=issued_by,
            )
        )
        return restriction

    def is_active(self, *, now: datetime | None = None) -> bool:
        current = now if now is not None else datetime.now(UTC)
        if current < self.starts_at:
            return False
        if self.ends_at is None:
            return True
        return current < self.ends_at


@dataclass(kw_only=True, eq=False)
class DoctorVerification(AggregateRoot):
    """Keyed by `doctor_id` (a real `app.modules.doctor` `Doctor.id`, read
    via the already-public, read-only `DoctorQueryPort` — no modification
    to that module) rather than bare `user_id`, so a "Verified Doctor
    Badge" is always tied to an actual onboarded `Doctor` record; `user_id`
    is stored alongside purely for display/query convenience, copied once
    from `DoctorSummaryDTO` at request time.

    Deliberately independent of `app.modules.doctor.domain.entities
    .DoctorLicense.verification_status` — that field verifies medical
    *license* authenticity as part of doctor onboarding; this aggregate is
    the community-facing trust badge this task asks for, with its own
    request/approve/reject/revoke lifecycle and no external medical-board
    integration (explicitly out of scope — "Do NOT implement external
    medical-license verification APIs"). `metadata` is the "extensible
    verification abstraction for future integration" the task asks for: an
    open `dict` a future integration can populate (submitted credentials,
    a verification-provider reference id, etc.) without a schema change.
    """

    doctor_id: UUID
    user_id: UUID
    organization_id: UUID
    status: VerificationStatus = VerificationStatus.PENDING
    specialty: str | None = None
    verifier_id: UUID | None = None
    verified_at: datetime | None = None
    rejection_reason: str | None = None
    revocation_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def request(
        cls,
        *,
        doctor_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        specialty: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "DoctorVerification":
        verification = cls(
            doctor_id=doctor_id,
            user_id=user_id,
            organization_id=organization_id,
            specialty=specialty,
            metadata=dict(metadata) if metadata is not None else {},
        )
        verification.record_event(
            DoctorVerificationRequested(
                verification_id=verification.id, doctor_id=doctor_id, user_id=user_id
            )
        )
        return verification

    def approve(self, *, verifier_id: UUID, specialty: str | None = None) -> None:
        if self.status is not VerificationStatus.PENDING:
            raise DoctorVerificationNotPendingError(self.id)
        self.status = VerificationStatus.VERIFIED
        self.verifier_id = verifier_id
        self.verified_at = datetime.now(UTC)
        if specialty is not None:
            self.specialty = specialty
        self.touch()
        self.record_event(
            DoctorVerificationApproved(
                verification_id=self.id, doctor_id=self.doctor_id, verifier_id=verifier_id
            )
        )

    def reject(self, *, verifier_id: UUID, reason: str) -> None:
        if self.status is not VerificationStatus.PENDING:
            raise DoctorVerificationNotPendingError(self.id)
        self.status = VerificationStatus.REJECTED
        self.verifier_id = verifier_id
        self.rejection_reason = reason
        self.touch()
        self.record_event(
            DoctorVerificationRejected(
                verification_id=self.id,
                doctor_id=self.doctor_id,
                verifier_id=verifier_id,
                reason=reason,
            )
        )

    def revoke(self, *, verifier_id: UUID, reason: str) -> None:
        if self.status is not VerificationStatus.VERIFIED:
            raise DoctorVerificationNotVerifiedError(self.id)
        self.status = VerificationStatus.REVOKED
        self.verifier_id = verifier_id
        self.revocation_reason = reason
        self.touch()
        self.record_event(
            DoctorVerificationRevoked(
                verification_id=self.id,
                doctor_id=self.doctor_id,
                verifier_id=verifier_id,
                reason=reason,
            )
        )

    def resubmit(
        self, *, specialty: str | None = None, metadata: dict[str, Any] | None = None
    ) -> None:
        if self.status not in (VerificationStatus.REJECTED, VerificationStatus.REVOKED):
            raise DoctorVerificationCannotBeResubmittedError(self.id)
        self.status = VerificationStatus.PENDING
        self.verifier_id = None
        self.verified_at = None
        self.rejection_reason = None
        self.revocation_reason = None
        if specialty is not None:
            self.specialty = specialty
        if metadata is not None:
            self.metadata = dict(metadata)
        self.touch()
        self.record_event(
            DoctorVerificationRequested(
                verification_id=self.id, doctor_id=self.doctor_id, user_id=self.user_id
            )
        )
