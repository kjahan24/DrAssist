"""SQLAlchemy ORM model for the Diagnosis module.

One table: `visit_diagnoses`. See `app.modules.diagnosis.container` for
the module's scope note.

`visit_diagnoses.organization_id` carries a real foreign key to
`organizations.id`, and `visit_id` a real foreign key to
`patient_visits.id` — brand-new columns on a brand-new table, so there is
no backward-compatibility reason to defer them; neither `organizations`
nor `patient_visits` is modified by this migration.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_chief_complaints.visit_id` already makes: a diagnosis has no
independent lifecycle meaning without its visit. `diagnosed_by`
(nullable, best-effort attribution) follows
`visit_chief_complaints.recorded_by`'s `SET NULL` choice — see that
column's own comment for the full reasoning.

Two uniqueness rules, both partial indexes scoped `WHERE deleted_at IS
NULL`:
- "sequence_number must be unique within a Visit" -> unique on
  `(visit_id, sequence_number)`, the same shape
  `visit_chief_complaints`' own sequence uniqueness already uses.
- "Only one Primary diagnosis is allowed per Visit" -> unique on
  `visit_id` additionally scoped `WHERE diagnosis_type = 'primary'`, the
  same *shape* `doctor_specializations`' "one primary per doctor" index
  uses — though enforcement at the application layer is rejection, not
  auto-unset; see `VisitDiagnosis`'s own docstring for why.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.diagnosis.domain.enums import DiagnosisStatus, DiagnosisType

_diagnosis_type_enum = pg_enum(DiagnosisType, "diagnosis_type_enum")
_diagnosis_status_enum = pg_enum(DiagnosisStatus, "diagnosis_status_enum")


class VisitDiagnosisModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "visit_diagnoses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    diagnosis_name: Mapped[str] = mapped_column(Text, nullable=False)
    icd10_code: Mapped[str | None] = mapped_column(Text, default=None)
    diagnosis_type: Mapped[DiagnosisType] = mapped_column(_diagnosis_type_enum, nullable=False)
    diagnosis_status: Mapped[DiagnosisStatus] = mapped_column(
        _diagnosis_status_enum, nullable=False, default=DiagnosisStatus.PROVISIONAL
    )
    clinical_notes: Mapped[str | None] = mapped_column(Text, default=None)
    diagnosed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    diagnosed_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_visit_diagnoses_visit_id_sequence_number",
            "visit_id",
            "sequence_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_visit_diagnoses_primary_per_visit",
            "visit_id",
            unique=True,
            postgresql_where=text("diagnosis_type = 'primary' AND deleted_at IS NULL"),
        ),
        Index("ix_visit_diagnoses_organization_id", "organization_id"),
        CheckConstraint("sequence_number >= 1", name="sequence_number_starts_at_one"),
        CheckConstraint(
            "NOT (diagnosis_type = 'primary' AND diagnosis_status = 'ruled_out')",
            name="primary_not_ruled_out",
        ),
    )
