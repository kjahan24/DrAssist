"""Schedule/Availability module aggregate roots: `DoctorSchedule`,
`DoctorTimeOff`.

**A pre-existing, differently-shaped `DoctorSchedule` already exists** at
`app.modules.doctor.domain.entities.DoctorSchedule` (fields: `doctor_id`,
`day_of_week`, `start_time`, `end_time`, `break_start`, `break_end`,
`is_available` — no `organization_id`, no `slot_duration_minutes`),
backed by its own `doctor_schedules` table, repository, and
`AddDoctorSchedule` use case. This task's own entity spec (`organization_id`,
`doctor_id`, `weekday`, `start_time`, `end_time`,
`slot_duration_minutes`, `is_active`) is materially different — it adds
tenant-scoping and appointment-slot sizing the existing entity has no
field for. Per rule 1 ("never modify previous modules unless absolutely
necessary") and rule 12 ("do NOT modify existing migrations — report
issues instead"), the existing `doctor.DoctorSchedule`/`doctor_schedules`
table is left completely untouched; this module's own `DoctorSchedule`
is a separate aggregate, in a separate table (`doctor_availabilities` —
deliberately *not* named `doctor_schedules`, to avoid a hard table-name
collision with the existing module), reachable only through this
module's own public port. See `container.py`'s scope note for the full
discussion — this duplication is a pre-existing architectural
inconsistency this task surfaces, not one it resolves; reconciling the
two is a decision for a future task, not something to silently resolve
here.

**No dedicated value object wraps `start_time`/`end_time` or
`start_datetime`/`end_datetime`.** The existing `doctor.DoctorSchedule`
already solves the identical "two time fields, one must be later than
the other" shape with two plain fields validated in `__post_init__`, not
a value object — no such value object exists anywhere in this codebase
to reuse (see `app.shared.domain.common_value_objects`), and introducing
one here would diverge from that established precedent (and from
`app.modules.appointment.domain.entities.Appointment`, which resolved
the identical question the same way) rather than follow it — see rule 8.

**"Doctor and Organization must match"** is made true *by construction*,
not validated after the fact: `organization_id` is not independently
caller-supplied anywhere in this module — the application layer derives
it from the referenced `Doctor`'s own summary (see
`application/services/schedule_consistency_service.py`), the same "true
by construction" technique every prior child-document module in this
codebase uses.

**"A doctor cannot have overlapping schedules on the same weekday"** /
**"A doctor cannot have overlapping time-off periods"** are cross-row
invariants (checked against sibling rows for the same doctor), so they
cannot live in `__post_init__` — both are enforced by the application
layer before construction, querying siblings first via each aggregate's
own `overlaps_with()` pure-logic method — the same "query first, then
construct" technique, and the same `overlaps_with()` shape, `doctor
.DoctorSchedule` itself already establishes (reused here almost
verbatim). Following that same precedent, there is no database-level
exclusion constraint (e.g. a Postgres `EXCLUDE` constraint) backing
either overlap rule — the existing `doctor_schedules` table has none
either, so adding one here would be a materially more sophisticated
enforcement mechanism than this codebase's own precedent for the
identical concern, not something this task asked for.

**"Inactive schedules are ignored"** means an inactive `DoctorSchedule`
never participates in overlap-detection against a new/updated sibling —
enforced by the application layer only ever comparing a candidate
against *active* siblings (see
`application/use_cases/create_doctor_schedule.py`), not by anything in
this file. `DoctorTimeOff` has no `is_active` field at all — nothing in
this task's field list describes one, so none was added (rule 10).

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime, time
from uuid import UUID

from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.events import (
    DoctorScheduleActiveChanged,
    DoctorScheduleCreated,
    DoctorScheduleUpdated,
    DoctorTimeOffCreated,
    DoctorTimeOffUpdated,
)
from app.modules.schedule.domain.exceptions import (
    InvalidScheduleTimeRangeError,
    InvalidSlotDurationError,
    InvalidTimeOffRangeError,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class DoctorSchedule(AggregateRoot):
    organization_id: UUID
    doctor_id: UUID
    weekday: Weekday
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.end_time <= self.start_time:
            raise InvalidScheduleTimeRangeError()
        if self.slot_duration_minutes <= 0:
            raise InvalidSlotDurationError()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        doctor_id: UUID,
        weekday: Weekday,
        start_time: time,
        end_time: time,
        slot_duration_minutes: int,
        is_active: bool = True,
    ) -> "DoctorSchedule":
        schedule = cls(
            organization_id=organization_id,
            doctor_id=doctor_id,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            slot_duration_minutes=slot_duration_minutes,
            is_active=is_active,
        )
        schedule.record_event(
            DoctorScheduleCreated(
                schedule_id=schedule.id,
                organization_id=organization_id,
                doctor_id=doctor_id,
            )
        )
        return schedule

    def overlaps_with(self, other: "DoctorSchedule") -> bool:
        """Pure time-range overlap check — the caller is responsible for
        first filtering to entries for the same `doctor_id`, the same
        `weekday`, and `is_active` (see the module docstring); this
        method deliberately checks none of those itself, since "overlap"
        is purely a time-range concept once two entries are known to
        share a doctor and a weekday — the identical shape
        `app.modules.doctor.domain.entities.DoctorSchedule
        .overlaps_with()` already establishes."""
        return self.start_time < other.end_time and other.start_time < self.end_time

    def update_details(
        self,
        *,
        start_time: time | None = None,
        end_time: time | None = None,
        slot_duration_minutes: int | None = None,
    ) -> None:
        """`None` means "leave unchanged" for every parameter.
        Re-validates both invariants against the *effective* values —
        the same partial-update convention
        `app.modules.icd10_coding.domain.entities.ICD10Coding
        .update_details()` uses. Re-checking "no overlap with siblings"
        against the effective time range is the application layer's
        responsibility (requires I/O) — see
        `application/use_cases/update_doctor_schedule.py`."""
        effective_start = start_time if start_time is not None else self.start_time
        effective_end = end_time if end_time is not None else self.end_time
        if effective_end <= effective_start:
            raise InvalidScheduleTimeRangeError()

        effective_slot_duration = (
            slot_duration_minutes
            if slot_duration_minutes is not None
            else self.slot_duration_minutes
        )
        if effective_slot_duration <= 0:
            raise InvalidSlotDurationError()

        self.start_time = effective_start
        self.end_time = effective_end
        self.slot_duration_minutes = effective_slot_duration

        self.touch()
        self.record_event(DoctorScheduleUpdated(schedule_id=self.id))

    def activate(self) -> None:
        self._set_active(True)

    def deactivate(self) -> None:
        self._set_active(False)

    def _set_active(self, is_active: bool) -> None:
        if self.is_active is is_active:
            return
        self.is_active = is_active
        self.touch()
        self.record_event(DoctorScheduleActiveChanged(schedule_id=self.id, is_active=is_active))


@dataclass(kw_only=True, eq=False)
class DoctorTimeOff(AggregateRoot):
    organization_id: UUID
    doctor_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.end_datetime <= self.start_datetime:
            raise InvalidTimeOffRangeError()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        doctor_id: UUID,
        start_datetime: datetime,
        end_datetime: datetime,
        reason: str | None = None,
    ) -> "DoctorTimeOff":
        time_off = cls(
            organization_id=organization_id,
            doctor_id=doctor_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            reason=reason,
        )
        time_off.record_event(
            DoctorTimeOffCreated(
                time_off_id=time_off.id,
                organization_id=organization_id,
                doctor_id=doctor_id,
            )
        )
        return time_off

    def overlaps_with(self, other: "DoctorTimeOff") -> bool:
        """Pure datetime-range overlap check — the caller is responsible
        for first filtering to entries for the same `doctor_id`, the
        same shape `DoctorSchedule.overlaps_with()` uses for its own
        weekday-scoped comparison."""
        return self.start_datetime < other.end_datetime and other.start_datetime < self.end_datetime

    def update_details(
        self,
        *,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        reason: str | None = None,
    ) -> None:
        """`None` means "leave unchanged" for every parameter. Re-checking
        "no overlap with siblings" against the effective datetime range
        is the application layer's responsibility (requires I/O) — see
        `application/use_cases/update_doctor_time_off.py`."""
        effective_start = start_datetime if start_datetime is not None else self.start_datetime
        effective_end = end_datetime if end_datetime is not None else self.end_datetime
        if effective_end <= effective_start:
            raise InvalidTimeOffRangeError()

        self.start_datetime = effective_start
        self.end_datetime = effective_end
        if reason is not None:
            self.reason = reason

        self.touch()
        self.record_event(DoctorTimeOffUpdated(time_off_id=self.id))
