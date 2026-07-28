"""SQLAlchemy ORM model for the Visit module.

One table: `patient_visits`. See `app.modules.visit.container` for the
module's scope note.

`patient_visits.organization_id`/`patient_id` carry real foreign keys to
`organizations.id`/`patients.id`, and `doctor_id` a real foreign key to
`doctors.id` — brand-new columns on a brand-new table, so there is no
backward-compatibility reason to defer them; neither `organizations`,
`patients`, nor `doctors` is modified by this migration.

`doctor_id` uses `ON DELETE RESTRICT` rather than `SET NULL`: unlike
`patient_allergies.verified_by`/`patient_medications.prescribed_by`/
`patient_medical_conditions.diagnosed_by` (nullable, best-effort
attribution fields), `doctor_id` here is *required* ("one visit belongs
to one doctor") — a `NOT NULL` column cannot use `SET NULL`, and `CASCADE`
would silently destroy visit history if a doctor row were ever removed,
so `RESTRICT` (matching `doctors.organization_id`/`doctors.user_id`'s own
choice for required, significant relationships) is the only safe option.

`appointment_id` is a plain nullable UUID column with **no** foreign key
— the Appointment module doesn't exist yet ("appointment_id is optional"
is the only rule this task specifies for it); adding a real FK to a
not-yet-built table isn't possible, and there is nothing to validate its
existence against yet either.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.visit.domain.enums import VisitPriority, VisitStatus, VisitType

_visit_type_enum = pg_enum(VisitType, "visit_type_enum")
_visit_status_enum = pg_enum(VisitStatus, "visit_status_enum")
_visit_priority_enum = pg_enum(VisitPriority, "visit_priority_enum")


class PatientVisitModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "patient_visits"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    visit_number: Mapped[str] = mapped_column(Text, nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    visit_type: Mapped[VisitType] = mapped_column(_visit_type_enum, nullable=False)
    visit_status: Mapped[VisitStatus] = mapped_column(
        _visit_status_enum, nullable=False, default=VisitStatus.SCHEDULED
    )
    priority: Mapped[VisitPriority] = mapped_column(
        _visit_priority_enum, nullable=False, default=VisitPriority.NORMAL
    )
    visit_date: Mapped[date] = mapped_column(nullable=False)
    check_in_time: Mapped[datetime | None] = mapped_column(default=None)
    consultation_start_time: Mapped[datetime | None] = mapped_column(default=None)
    consultation_end_time: Mapped[datetime | None] = mapped_column(default=None)
    check_out_time: Mapped[datetime | None] = mapped_column(default=None)
    chief_complaint_summary: Mapped[str | None] = mapped_column(Text, default=None)
    reason_for_visit: Mapped[str | None] = mapped_column(Text, default=None)
    room_number: Mapped[str | None] = mapped_column(Text, default=None)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    follow_up_date: Mapped[date | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_patient_visits_organization_id_visit_number",
            "organization_id",
            "visit_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_patient_visits_organization_id", "organization_id"),
        Index("ix_patient_visits_patient_id", "patient_id"),
        Index("ix_patient_visits_doctor_id", "doctor_id"),
        CheckConstraint(
            "check_in_time IS NULL OR check_out_time IS NULL OR check_out_time >= check_in_time",
            name="check_out_not_before_check_in",
        ),
        CheckConstraint(
            "consultation_start_time IS NULL OR consultation_end_time IS NULL "
            "OR consultation_end_time >= consultation_start_time",
            name="consultation_end_not_before_start",
        ),
        CheckConstraint(
            "NOT follow_up_required OR follow_up_date IS NOT NULL",
            name="follow_up_date_required",
        ),
    )
