"""SQLAlchemy ORM model for the Chief Complaints module.

One table: `visit_chief_complaints`. See
`app.modules.chief_complaints.container` for the module's scope note.

`visit_chief_complaints.organization_id` carries a real foreign key to
`organizations.id`, and `visit_id` a real foreign key to
`patient_visits.id` — brand-new columns on a brand-new table, so there is
no backward-compatibility reason to defer them; neither `organizations`
nor `patient_visits` is modified by this migration.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_vital_signs.visit_id` already makes: a chief complaint has no
independent lifecycle meaning without its visit. `recorded_by` (nullable,
best-effort attribution) follows `visit_vital_signs.recorded_by`'s
`SET NULL` choice — see that column's own comment for the full reasoning.
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
from app.modules.chief_complaints.domain.enums import DurationUnit, Onset, Severity

_duration_unit_enum = pg_enum(DurationUnit, "duration_unit_enum")
_severity_enum = pg_enum(Severity, "severity_enum")
_onset_enum = pg_enum(Onset, "onset_enum")


class VisitChiefComplaintModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "visit_chief_complaints"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    duration_value: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    duration_unit: Mapped[DurationUnit | None] = mapped_column(_duration_unit_enum, default=None)
    severity: Mapped[Severity | None] = mapped_column(_severity_enum, default=None)
    onset: Mapped[Onset | None] = mapped_column(_onset_enum, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    recorded_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_visit_chief_complaints_visit_id_sequence_number",
            "visit_id",
            "sequence_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_visit_chief_complaints_organization_id", "organization_id"),
        CheckConstraint("sequence_number >= 1", name="sequence_number_starts_at_one"),
        CheckConstraint(
            "duration_value IS NULL OR duration_value >= 0", name="duration_value_nonneg"
        ),
        CheckConstraint(
            "duration_value IS NOT NULL OR duration_unit IS NULL",
            name="duration_unit_requires_value",
        ),
    )
