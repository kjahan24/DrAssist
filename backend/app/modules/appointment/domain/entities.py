"""Appointment module aggregate root: `Appointment`.

`Appointment` is **not** a duplicate of `Visit` and **not** `ClinicalNote`:
it represents the scheduling event ("patient X is booked with doctor Y at
time Z"), independent of whatever clinical encounter eventually happens
because of it. `organization_id` is not independently caller-supplied:
the application layer derives it from the linked `Patient`'s own summary
and *validates* (not merely assumes) that the linked `Doctor` belongs to
that same organization — "Patient and Doctor must belong to the same
Organization" is therefore a real runtime check, not something made true
by construction the way a single-parent derivation would — see
`application/services/appointment_consistency_service.py`.

**No dedicated value object wraps `start_time`/`end_time`.** This was
considered and rejected: the closest existing precedent for exactly this
"two `time` fields, one must be later than the other" shape is
`app.modules.doctor.domain.entities.DoctorSchedule`, which — after already
solving this same problem — uses two plain `time` fields validated in
`__post_init__`, not a `TimeRange` value object; no such value object
exists anywhere in this codebase to reuse (see
`app.shared.domain.common_value_objects`). Introducing a new one here
would diverge from that established precedent rather than follow it — see
rule 8. `appointment_number` also has no value object, the same
"no format was specified" reasoning `app.modules.diagnosis.domain.entities`
already documents for its own `icd10_code`.

**"Completed appointments become immutable" / "NoShow appointments become
immutable"** are enforced by `ensure_editable()` (shared by
`update_details()` and every transition method) — `_EDITABLE_STATUSES`
deliberately *includes* `Cancelled`: only "Completed"/"NoShow" are
described as unconditionally immutable records; "Cancelled appointments
cannot become Completed" is a narrower rule about one specific
transition, not about the whole record, so a cancelled appointment's
`notes`/`reason_for_visit` remain editable — see `ensure_editable()`'s
own docstring.

**"Cancelled appointments cannot become Completed"** is satisfied by
making `Cancelled` a terminal *status* (no outgoing transitions at all in
`_ALLOWED_TRANSITIONS`): this task's Business Rules state only the one
forbidden transition and describe no resubmission/reactivation cycle, so
nothing beyond that is implemented — the same "only encode business rules
explicitly stated for the module being built" principle
`app.modules.doctor_review.domain.entities.DoctorReview` already
establishes for its own transition map.

**"One completed appointment may optionally create one Visit"** is
implemented as an optional `visit_id` parameter on `complete()` — the
domain layer never fetches or creates a `Visit` itself (this module
performs no I/O); the application layer validates the referenced visit
(if given) through `VisitQueryPort` before calling `complete()` — see
`application/use_cases/complete_appointment.py`.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from uuid import UUID

from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.domain.events import (
    AppointmentCreated,
    AppointmentStatusChanged,
    AppointmentUpdated,
)
from app.modules.appointment.domain.exceptions import (
    AppointmentNotEditableError,
    AppointmentNumberRequiredError,
    InvalidAppointmentStatusTransitionError,
    InvalidAppointmentTimeRangeError,
)
from app.shared.domain.entity import AggregateRoot

_EDITABLE_STATUSES = frozenset(
    {
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
    }
)

_ALLOWED_TRANSITIONS: dict[AppointmentStatus, frozenset[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: frozenset(
        {
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.CANCELLED,
            AppointmentStatus.NO_SHOW,
        }
    ),
    AppointmentStatus.CONFIRMED: frozenset(
        {AppointmentStatus.CHECKED_IN, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW}
    ),
    AppointmentStatus.CHECKED_IN: frozenset(
        {AppointmentStatus.IN_PROGRESS, AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED}
    ),
    AppointmentStatus.IN_PROGRESS: frozenset(
        {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED}
    ),
    AppointmentStatus.COMPLETED: frozenset(),
    AppointmentStatus.CANCELLED: frozenset(),
    AppointmentStatus.NO_SHOW: frozenset(),
}


@dataclass(kw_only=True, eq=False)
class Appointment(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_number: str
    appointment_date: date
    start_time: time
    end_time: time
    appointment_type: AppointmentType
    status: AppointmentStatus
    reason_for_visit: str | None = None
    notes: str | None = None
    booked_by_user_id: UUID | None = None
    visit_id: UUID | None = None
    checked_in_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.appointment_number or not self.appointment_number.strip():
            raise AppointmentNumberRequiredError()
        self.appointment_number = self.appointment_number.strip()
        if self.end_time <= self.start_time:
            raise InvalidAppointmentTimeRangeError()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        doctor_id: UUID,
        appointment_number: str,
        appointment_date: date,
        start_time: time,
        end_time: time,
        appointment_type: AppointmentType,
        reason_for_visit: str | None = None,
        notes: str | None = None,
        booked_by_user_id: UUID | None = None,
    ) -> "Appointment":
        appointment = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_number=appointment_number,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            appointment_type=appointment_type,
            status=AppointmentStatus.SCHEDULED,
            reason_for_visit=reason_for_visit,
            notes=notes,
            booked_by_user_id=booked_by_user_id,
        )
        appointment.record_event(
            AppointmentCreated(
                appointment_id=appointment.id,
                organization_id=organization_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
            )
        )
        return appointment

    def ensure_editable(self) -> None:
        """Shared by `update_details()` and every transition method:
        `status` must not already be `Completed`/`NoShow`. `Cancelled` is
        deliberately *not* blocked here — see the module docstring."""
        if self.status not in _EDITABLE_STATUSES:
            raise AppointmentNotEditableError()

    def update_details(
        self,
        *,
        appointment_date: date | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        appointment_type: AppointmentType | None = None,
        reason_for_visit: str | None = None,
        notes: str | None = None,
    ) -> None:
        """`None` means "leave unchanged" for every parameter. Re-validates
        "end_time must be later than start_time" against the *effective*
        values whenever either changes — the same partial-update
        convention `app.modules.icd10_coding.domain.entities.ICD10Coding
        .update_details()` uses."""
        self.ensure_editable()

        effective_start = start_time if start_time is not None else self.start_time
        effective_end = end_time if end_time is not None else self.end_time
        if effective_end <= effective_start:
            raise InvalidAppointmentTimeRangeError()

        if appointment_date is not None:
            self.appointment_date = appointment_date
        self.start_time = effective_start
        self.end_time = effective_end
        if appointment_type is not None:
            self.appointment_type = appointment_type
        if reason_for_visit is not None:
            self.reason_for_visit = reason_for_visit
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(AppointmentUpdated(appointment_id=self.id))

    def confirm(self) -> None:
        self._transition_to(AppointmentStatus.CONFIRMED)

    def check_in(self) -> None:
        self._transition_to(AppointmentStatus.CHECKED_IN)
        self.checked_in_at = datetime.now(UTC)

    def start(self) -> None:
        self._transition_to(AppointmentStatus.IN_PROGRESS)

    def complete(self, *, visit_id: UUID | None = None) -> None:
        """`visit_id` is optional — "one completed appointment may
        optionally create one Visit". The application layer is
        responsible for confirming, via `VisitQueryPort`, that the given
        visit actually exists and belongs to this same organization,
        patient, and doctor before calling this method — see the module
        docstring."""
        self._transition_to(AppointmentStatus.COMPLETED)
        self.completed_at = datetime.now(UTC)
        self.visit_id = visit_id

    def cancel(self) -> None:
        self._transition_to(AppointmentStatus.CANCELLED)
        self.cancelled_at = datetime.now(UTC)

    def mark_no_show(self) -> None:
        self._transition_to(AppointmentStatus.NO_SHOW)

    def _transition_to(self, target_status: AppointmentStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target_status not in allowed:
            raise InvalidAppointmentStatusTransitionError(self.status.value, target_status.value)
        self.status = target_status
        self.touch()
        self.record_event(
            AppointmentStatusChanged(appointment_id=self.id, status=target_status.value)
        )
