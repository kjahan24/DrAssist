"""Notification module aggregate root: `Notification`.

`organization_id` is not independently caller-supplied: the application
layer derives it from the recipient `User`'s own summary via
`NotificationConsistencyService.resolve_organization_for_recipient()`,
the same single-parent-derivation ("true by construction") technique
`app.modules.schedule.domain.entities.DoctorSchedule` already establishes
for `doctor_id` -> `organization_id` — "every notification belongs to one
organization" is therefore structurally guaranteed, not independently
validated. "Recipient existence" is enforced the same way: a recipient
that doesn't exist has no organization to derive, so the lookup itself
fails — see `application/services/notification_consistency_service.py`.

**`reference_type` is a plain nullable string, not a closed enum.** This
was considered and rejected: the closest existing precedent for an
optional polymorphic reference is
`app.modules.patient_history.domain.enums.ReferenceType`, an explicit
8-member enum, each existence-validated through a dedicated peer module's
public port. That approach does not transfer here for two reasons this
task itself states: (1) no enum of valid `reference_type` values is
given anywhere in the task's Entity/Enum specification (unlike
PatientHistory's own task, which named all 8 members explicitly), and
(2) the task's own "Integrate cleanly with ... Family / Caregiver
(future)" instruction lists a module that does not exist yet as one this
field must eventually be able to point into — a closed,
existence-validated enum cannot include a member for a module that isn't
built, so any enum written today would necessarily be incomplete. This
field is therefore a deliberately open, forward-compatible
discriminator: future producers (Appointment, Schedule, Visit, a future
Family/Caregiver module, etc.) choose their own `reference_type` string
when they create a notification, and no cross-module existence check is
performed against it — only "both set or both omitted" is validated, in
`__post_init__` below, since that is a genuine, self-contained invariant
requiring no I/O.

**No dedicated value object wraps `scheduled_at`/`expires_at`.** The
closest existing precedent for this "two optional datetime fields, one
ordering invariant" shape is
`app.modules.doctor.domain.entities.DoctorSchedule`
(`start_time`/`end_time`, mandatory, not optional) and
`app.modules.schedule.domain.entities.DoctorTimeOff`
(`start_datetime`/`end_datetime`, likewise mandatory) — both use two
plain fields validated in `__post_init__`, not a value object; no such
value object exists anywhere in this codebase to reuse. Introducing one
here would diverge from that established precedent — see rule 8. Unlike
those two precedents, both fields here are independently optional (a
notification may have neither, either, or both), so the ordering check
only applies when both are actually present.

**No `update_details()`/`ensure_editable()` mechanism exists on this
aggregate.** Every prior document-like module (`Appointment`,
`DoctorReview`, ...) supports post-creation editing of some of its own
fields, gated by an "editable while not yet in a terminal status" check.
No business rule stated for `Notification` asks for editing a
notification's own content (`title`/`message`/`priority`/etc.) after
creation — only status transitions are described — so no such mechanism
is built here; this is the same "only encode business rules explicitly
stated for the module being built" principle applied to *omit* a
mechanism rather than narrow one, the way
`app.modules.doctor_review.domain.entities.DoctorReview` already applies
it to its own transition map.

**Status transition map.** A notification starts `Scheduled` if created
with a `scheduled_at`, otherwise `Pending` — the same "derive the
starting state from a creation-time input" technique
`app.modules.icd10_coding.domain.entities.ICD10Coding` already uses for
its own `coding_source`-derived `review_status`. From there:
`Pending`/`Scheduled` -> `Sent` -> `Delivered` -> `Read`, with `Cancelled`
and `Expired` reachable only from `Pending`/`Scheduled` (before a
notification has actually gone out — cancelling or expiring something
already `Sent` has no real-world meaning). `Read`, `Cancelled`, and
`Expired` are all terminal (no outgoing transitions at all in
`_ALLOWED_TRANSITIONS`): this task's Business Rules state only three
specific forbidden transitions ("Read notifications cannot become
unread", "Expired notifications cannot be sent", "Cancelled
notifications cannot be delivered") and describe no reactivation cycle
for any of them, so nothing beyond making each one a dead end is
implemented — the same principle `Appointment.status`'s own `Completed`/
`Cancelled`/`NoShow` terminal states already establish.

`mark_sent()` additionally checks `expires_at` against the current time
before allowing the transition, raising `NotificationExpiredError` if the
deadline has already passed. This is the only way "Expired notifications
cannot be sent" is enforceable without a Background Job (explicitly out
of scope for this task — see `container.py`'s scope note): there is no
scheduled sweep that would otherwise flip a stale `Pending`/`Scheduled`
notification to `Expired` before something tries to send it. The
comparison uses `datetime.now(UTC)`, the same pattern every other
aggregate in this codebase already uses for its own timestamp stamping
(e.g. `Appointment.check_in()`'s `checked_in_at`) — it is not I/O, so it
does not violate the domain layer's own "no I/O" rule. `mark_expired()`
itself is *not* additionally gated on `expires_at` having passed: no
business rule states that constraint, and a future caller (a Background
Job sweep, once built, or a manual administrative action) is expected to
decide for itself when to call it.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.modules.notification.domain.events import NotificationCreated, NotificationStatusChanged
from app.modules.notification.domain.exceptions import (
    InvalidNotificationReferenceError,
    InvalidNotificationScheduleError,
    InvalidNotificationStatusTransitionError,
    NotificationExpiredError,
    NotificationMessageRequiredError,
    NotificationTitleRequiredError,
)
from app.shared.domain.entity import AggregateRoot

_ALLOWED_TRANSITIONS: dict[NotificationStatus, frozenset[NotificationStatus]] = {
    NotificationStatus.PENDING: frozenset(
        {NotificationStatus.SENT, NotificationStatus.CANCELLED, NotificationStatus.EXPIRED}
    ),
    NotificationStatus.SCHEDULED: frozenset(
        {NotificationStatus.SENT, NotificationStatus.CANCELLED, NotificationStatus.EXPIRED}
    ),
    NotificationStatus.SENT: frozenset({NotificationStatus.DELIVERED}),
    NotificationStatus.DELIVERED: frozenset({NotificationStatus.READ}),
    NotificationStatus.READ: frozenset(),
    NotificationStatus.CANCELLED: frozenset(),
    NotificationStatus.EXPIRED: frozenset(),
}


@dataclass(kw_only=True, eq=False)
class Notification(AggregateRoot):
    organization_id: UUID
    recipient_user_id: UUID
    notification_type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    status: NotificationStatus
    reference_type: str | None = None
    reference_id: UUID | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise NotificationTitleRequiredError()
        self.title = self.title.strip()

        if not self.message or not self.message.strip():
            raise NotificationMessageRequiredError()
        self.message = self.message.strip()

        if (self.reference_type is None) != (self.reference_id is None):
            raise InvalidNotificationReferenceError()

        if (
            self.scheduled_at is not None
            and self.expires_at is not None
            and self.scheduled_at > self.expires_at
        ):
            raise InvalidNotificationScheduleError()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        recipient_user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        scheduled_at: datetime | None = None,
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Notification":
        status = (
            NotificationStatus.SCHEDULED if scheduled_at is not None else NotificationStatus.PENDING
        )
        notification = cls(
            organization_id=organization_id,
            recipient_user_id=recipient_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            status=status,
            reference_type=reference_type,
            reference_id=reference_id,
            scheduled_at=scheduled_at,
            expires_at=expires_at,
            metadata=metadata,
        )
        notification.record_event(
            NotificationCreated(
                notification_id=notification.id,
                organization_id=organization_id,
                recipient_user_id=recipient_user_id,
                notification_type=notification_type.value,
            )
        )
        return notification

    def mark_sent(self) -> None:
        """`(Pending|Scheduled) -> Sent`. The transition-validity check
        runs *before* the expiry check: an already-`Expired` (or
        otherwise terminal) notification raises
        `InvalidNotificationStatusTransitionError`, the same as any other
        disallowed transition, rather than `NotificationExpiredError` —
        that error is reserved for the specific case this check exists
        for: a `Pending`/`Scheduled` notification whose `expires_at`
        deadline has passed without anyone having called
        `mark_expired()` yet. See the module docstring for why this
        check lives here at all rather than relying solely on a prior
        `mark_expired()` call."""
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if NotificationStatus.SENT not in allowed:
            raise InvalidNotificationStatusTransitionError(
                self.status.value, NotificationStatus.SENT.value
            )
        if self.expires_at is not None and datetime.now(UTC) >= self.expires_at:
            raise NotificationExpiredError(self.id)
        self._transition_to(NotificationStatus.SENT)
        self.sent_at = datetime.now(UTC)

    def mark_delivered(self) -> None:
        self._transition_to(NotificationStatus.DELIVERED)

    def mark_read(self) -> None:
        self._transition_to(NotificationStatus.READ)
        self.read_at = datetime.now(UTC)

    def cancel(self) -> None:
        self._transition_to(NotificationStatus.CANCELLED)

    def mark_expired(self) -> None:
        self._transition_to(NotificationStatus.EXPIRED)

    def _transition_to(self, target_status: NotificationStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target_status not in allowed:
            raise InvalidNotificationStatusTransitionError(self.status.value, target_status.value)
        self.status = target_status
        self.touch()
        self.record_event(
            NotificationStatusChanged(notification_id=self.id, status=target_status.value)
        )
