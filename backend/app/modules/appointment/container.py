"""Module composition root.

The one place `AppointmentQueryPort` gets bound to its concrete
implementation (`AppointmentFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_appointment_facade(session)` rather
than constructing `AppointmentFacade` (or the repository) directly.

Scope note — this task builds the Appointment module's **foundation**
only: the `Appointment` aggregate (the scheduling event itself — *not* a
duplicate of `Visit`, *not* `ClinicalNote`), its repository,
`CreateAppointment` (which derives `organization_id` from the linked
`Patient` and *validates* it against the linked `Doctor`'s own
organization via `AppointmentConsistencyService`, and enforces "globally
unique" `appointment_number`), `UpdateAppointment` (reschedule/detail
edits while editable), `ConfirmAppointment`, `CheckInAppointment`,
`StartAppointment`, `CompleteAppointment` (which optionally records a
link to an already-existing `Visit`, validated through `VisitQueryPort`
— this module never creates a `Visit` itself), `CancelAppointment`, and
`MarkAppointmentNoShow` (which together enforce "valid status
transitions" via an explicit transition map, and "Completed/NoShow
appointments become immutable" via `ensure_editable()`), and the public
query facade.

This module deliberately does **not** build Schedule/Availability (no
doctor-working-hours/slot-conflict checking — see
`app.modules.doctor.domain.entities.DoctorSchedule` for that module's own
existing, separate foundation), Calendar, Notification, SMS/Email
Reminders, Queue Management, Telemedicine session handling, Patient
Portal, or any Google/Outlook Calendar sync, any AI integration, or any
HTTP endpoint (per this task's explicit exclusions), and does not modify
the Authentication, Organization, Doctor, Patient, Visit, Vital Signs,
Chief Complaints, Diagnosis, Procedures, Attachments, Clinical Notes,
SOAP Notes, Prescription, Lab Orders, Lab Results, Clinical Reasoning,
Differential Diagnosis, ICD-10 Coding, Doctor Review, or Patient
History modules or their tables — this module only *reads* four of them
(Patient, Doctor, Authentication, Visit) through their public ports.

Schedule/Availability, Calendar, Notification, SMS Reminder, Email
Reminder, Queue Management, Telemedicine, Patient Portal, Google
Calendar, and Outlook Calendar are explicitly out of scope for this
task — they are expected to become their own modules (or integrations),
each depending on `AppointmentQueryPort` (keyed by `appointment_id`,
`appointment_number`, or `list_appointments_for_patient`/
`list_appointments_for_doctor` for the parent-scoped views) the same way
this module itself depends on its four peer modules' ports. Nothing
about this schema needs to change to support them: `appointment_date`/
`start_time`/`end_time` already give a Calendar/Google-Calendar-sync
consumer everything it needs to render a slot, and `status` already
gives Queue Management/Notification consumers the state machine to react
to via `AppointmentStatusChanged`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointment.application.services.appointment_query_service import (
    AppointmentQueryService,
)
from app.modules.appointment.infrastructure.repositories import SqlAlchemyAppointmentRepository
from app.modules.appointment.public.facade import AppointmentFacade


def build_appointment_facade(session: AsyncSession) -> AppointmentFacade:
    """Construct an `AppointmentFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    appointment_repository = SqlAlchemyAppointmentRepository(session)

    query_service = AppointmentQueryService(appointment_repository=appointment_repository)

    return AppointmentFacade(query_service=query_service)
