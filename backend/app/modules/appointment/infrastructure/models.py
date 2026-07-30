"""SQLAlchemy ORM model for the Appointment module.

One table: `appointments`. See `app.modules.appointment.container` for
the module's scope note.

`organization_id` carries a real foreign key to `organizations.id`,
`patient_id` to `patients.id`, `doctor_id` to `doctors.id`,
`booked_by_user_id` (nullable) to `users.id`, and `visit_id` (nullable)
to `patient_visits.id` — brand-new columns on a brand-new table, so
there is no backward-compatibility reason to defer them; none of
`organizations`, `patients`, `doctors`, `users`, or `patient_visits` is
modified by this migration.

`patient_id` uses `ON DELETE CASCADE`, matching every prior module's own
choice for that column. `organization_id`/`doctor_id` use `ON DELETE
RESTRICT`, matching every other module's treatment of those two columns.
`booked_by_user_id` uses `ON DELETE SET NULL`, the same treatment
`created_by`/`updated_by` already receive — this is an optional record of
who booked the appointment, not an ownership relationship. `visit_id`
also uses `ON DELETE SET NULL`: it is an optional cross-reference to a
peer document ("one completed appointment *may optionally* create one
Visit"), not an ownership relationship, so a hard-deleted `patient_visits`
row should clear this link rather than cascading the deletion or
blocking it — the same treatment `differential_diagnoses
.clinical_reasoning_id`/`icd10_codes.differential_diagnosis_id` already
receive for their own optional peer-document references.

"Appointment number must be globally unique" is enforced by a plain
(non-composite — deliberately *not* scoped to `organization_id`, per the
task's own wording) partial unique index on `appointment_number WHERE
deleted_at IS NULL`.

"Appointment end_time must be later than start_time" has a `CHECK`
constraint in addition to `Appointment.__post_init__`'s own validation —
the same defense-in-depth precedent `app.modules.doctor.infrastructure
.models.DoctorScheduleModel`'s own `start_before_end` constraint already
establishes for the identical field shape.

There is no `CHECK` constraint for "valid status transitions",
"Completed/NoShow become immutable", or "Patient and Doctor must belong
to the same Organization": a `CHECK` constraint can only see this table's
own row, never the *previous* value of `status` or another table's
`organization_id` column, so all three are enforced exclusively at the
application layer.
"""

import uuid
from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType

_appointment_type_enum = pg_enum(AppointmentType, "appointment_type_enum")
_appointment_status_enum = pg_enum(AppointmentStatus, "appointment_status_enum")


class AppointmentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "appointments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    appointment_number: Mapped[str] = mapped_column(Text, nullable=False)
    appointment_date: Mapped[date] = mapped_column(nullable=False)
    start_time: Mapped[time] = mapped_column(nullable=False)
    end_time: Mapped[time] = mapped_column(nullable=False)
    appointment_type: Mapped[AppointmentType] = mapped_column(
        _appointment_type_enum, nullable=False
    )
    status: Mapped[AppointmentStatus] = mapped_column(_appointment_status_enum, nullable=False)
    reason_for_visit: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    booked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="SET NULL"), default=None
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    cancelled_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_appointments_appointment_number",
            "appointment_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_appointments_organization_id", "organization_id"),
        Index("ix_appointments_patient_id", "patient_id"),
        Index("ix_appointments_doctor_id", "doctor_id"),
        Index("ix_appointments_doctor_id_appointment_date", "doctor_id", "appointment_date"),
        Index("ix_appointments_visit_id", "visit_id"),
        Index("ix_appointments_booked_by_user_id", "booked_by_user_id"),
        CheckConstraint("end_time > start_time", name="end_time_after_start_time"),
    )
