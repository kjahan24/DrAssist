"""Module composition root.

The one place `ScheduleQueryPort` gets bound to its concrete
implementation (`ScheduleFacade`), and both repository interfaces get
bound to their SQLAlchemy implementations. Any future module's
`api/dependencies.py` calls `build_schedule_facade(session)` rather than
constructing `ScheduleFacade` (or either repository) directly.

**A note on a pre-existing naming collision.** `app.modules.doctor
.domain.entities.DoctorSchedule` already exists — a doctor's own
recurring availability windows (`doctor_id`, `day_of_week`, `start_time`,
`end_time`, `break_start`, `break_end`, `is_available`), backed by its
own `doctor_schedules` table, repository, and `AddDoctorSchedule` use
case, with its own overlap-prevention logic already working. This
task's own `DoctorSchedule` spec (`organization_id`, `doctor_id`,
`weekday`, `start_time`, `end_time`, `slot_duration_minutes`,
`is_active`) is a *materially different* shape — it adds tenant-scoping
and appointment-slot sizing the existing entity has no field for, and
this task explicitly names "Schedule / Availability" as its own
top-level module (integrating with Organization/Doctor/Appointment as
peers), not as an extension of `app.modules.doctor`.

Per rule 1 ("never modify previous modules unless absolutely
necessary") and rule 12 ("do NOT modify existing migrations — report
issues instead of rewriting migration history"), the existing
`doctor.DoctorSchedule`/`doctor_schedules` table, repository, and
`AddDoctorSchedule` use case are left **completely untouched** — this
task does not add `organization_id`/`slot_duration_minutes` to that
table, does not rename `day_of_week`/`is_available`, and does not delete
or deprecate anything there. Instead, this module builds its own,
separate `DoctorSchedule`/`DoctorTimeOff` aggregates in their own tables
(`doctor_availabilities`, `doctor_time_off_periods` — deliberately not
named `doctor_schedules`, to avoid a hard table-name collision),
reachable only through this module's own `ScheduleQueryPort`. **This
duplication is a pre-existing architectural inconsistency this task
surfaces, not one it silently resolves** — reconciling the two
`DoctorSchedule` concepts (e.g. deprecating/migrating away from the one
in `app.modules.doctor` in favor of this module, or clarifying they
serve genuinely different purposes) is a decision for a future task; see
this task's own "Implementation Summary" / "Compatibility Changes" for
the same disclosure.

Scope note — this task builds the Schedule/Availability module's
**foundation** only: `DoctorSchedule` (a doctor's own tenant-scoped,
appointment-slot-sized weekly availability window — "one doctor may
have multiple weekly schedules") and `DoctorTimeOff` (a doctor's own
tenant-scoped unavailability period), their repositories,
`CreateDoctorSchedule`/`UpdateDoctorSchedule`/`ActivateDoctorSchedule`/
`DeactivateDoctorSchedule` (which together derive `organization_id` from
the linked `Doctor` via `ScheduleConsistencyService`, enforce "end_time
must be later than start_time", "slot_duration_minutes must be greater
than zero", and "no overlapping *active* schedules on the same
weekday"), `CreateDoctorTimeOff`/`UpdateDoctorTimeOff` (which enforce
"end_datetime must be later than start_datetime" and "no overlapping
time-off periods"), and the public query facade.

This module deliberately does **not** build Appointment logic (no
slot-booking, no conflict-checking against actual `Appointment` rows —
"Existing appointments are NOT modified by this module", and this module
never even *reads* `AppointmentQueryPort`: defining availability *rules*
does not require knowing which specific slots are already booked, which
is exactly the Appointment Booking concern this task excludes),
Notification, Calendar UI, any AI integration, or any HTTP endpoint, and
does not modify the Authentication, Organization, Doctor, Patient,
Visit, Vital Signs, Chief Complaints, Diagnosis, Procedures, Attachments,
Clinical Notes, SOAP Notes, Prescription, Lab Orders, Lab Results,
Clinical Reasoning, Differential Diagnosis, ICD-10 Coding, Doctor
Review, Patient History, or Appointment modules or their tables — this
module only *reads* Doctor through its public port.

**Update — the ownership decision above has now been made** by the
Architecture Review & Cleanup task (see
`docs/backend-architecture/14_doctor_schedule_ownership.md`): this
module's `DoctorSchedule`/`DoctorTimeOff` are the canonical, go-forward
owner of "doctor schedule/availability" — they alone are tenant-scoped
and alone carry `slot_duration_minutes`, satisfying this codebase's own
load-bearing multi-tenancy convention and the stated future need to
generate bookable appointment slots.
`app.modules.doctor.domain.entities.DoctorSchedule` is now formally
deprecated (see its own docstring) but intentionally left running,
unmigrated, and fully backward-compatible: no confirmed zero-consumer
guarantee exists for its two live REST endpoints, so removing or
rewriting it was out of scope for a review task bound by "never modify
public APIs unless absolutely necessary" and "never rewrite migration
history." No schema, table, or route in either module changed as a
result of this decision — it is a documentation-only clarification of
an already-existing state.

Calendar, Appointment Booking, Google Calendar, Outlook Calendar,
Holiday Management, Recurring Availability, Resource Scheduling, and
Notification Module are explicitly out of scope for this task — they
are expected to become their own modules (or integrations), each
depending on `ScheduleQueryPort` (keyed by `schedule_id`/`time_off_id`,
or `list_doctor_schedules`/`list_active_doctor_schedules_for_weekday`/
`list_doctor_time_off` for the doctor-scoped views) the same way this
module itself depends on Doctor's own port. Nothing about this schema
needs to change to support them: `weekday`/`start_time`/`end_time`/
`slot_duration_minutes` already give a future Appointment Booking module
everything it needs to generate bookable slots, and `is_active` already
lets a doctor pause a recurring window without deleting it.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schedule.application.services.doctor_schedule_query_service import (
    DoctorScheduleQueryService,
)
from app.modules.schedule.application.services.doctor_time_off_query_service import (
    DoctorTimeOffQueryService,
)
from app.modules.schedule.infrastructure.repositories import (
    SqlAlchemyDoctorScheduleRepository,
    SqlAlchemyDoctorTimeOffRepository,
)
from app.modules.schedule.public.facade import ScheduleFacade


def build_schedule_facade(session: AsyncSession) -> ScheduleFacade:
    """Construct a `ScheduleFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    doctor_schedule_repository = SqlAlchemyDoctorScheduleRepository(session)
    doctor_time_off_repository = SqlAlchemyDoctorTimeOffRepository(session)

    doctor_schedule_query_service = DoctorScheduleQueryService(
        doctor_schedule_repository=doctor_schedule_repository
    )
    doctor_time_off_query_service = DoctorTimeOffQueryService(
        doctor_time_off_repository=doctor_time_off_repository
    )

    return ScheduleFacade(
        doctor_schedule_query_service=doctor_schedule_query_service,
        doctor_time_off_query_service=doctor_time_off_query_service,
    )
