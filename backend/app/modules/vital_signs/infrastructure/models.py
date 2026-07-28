"""SQLAlchemy ORM model for the Vital Signs module.

One table: `visit_vital_signs`. See `app.modules.vital_signs.container`
for the module's scope note.

`visit_vital_signs.organization_id` carries a real foreign key to
`organizations.id`, and `visit_id` a real foreign key to
`patient_visits.id` — brand-new columns on a brand-new table, so there is
no backward-compatibility reason to defer them; neither `organizations`
nor `patient_visits` is modified by this migration.

`visit_id` uses `ON DELETE CASCADE`, not `RESTRICT`: unlike
`patient_visits.doctor_id` (a required, significant relationship whose
loss would silently destroy visit history), a vital signs record has no
independent lifecycle meaning without its visit — the same reasoning
`doctor_profiles.doctor_id` already applies for the identical
one-to-one-with-CASCADE shape. `recorded_by` (nullable, best-effort
attribution) follows `patient_allergies.verified_by`'s `SET NULL` choice
instead — see that column's own comment for the full reasoning.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, SmallInteger, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class VisitVitalSignsModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "visit_vital_signs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    bmi: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), default=None)
    temperature_c: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    pulse_bpm: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    respiratory_rate: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    systolic_bp: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    diastolic_bp: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    spo2: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    blood_glucose: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), default=None)
    pain_score: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    recorded_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_visit_vital_signs_visit_id",
            "visit_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_visit_vital_signs_organization_id", "organization_id"),
        CheckConstraint("systolic_bp > diastolic_bp", name="systolic_gt_diastolic"),
        CheckConstraint("spo2 >= 0 AND spo2 <= 100", name="spo2_in_range"),
        CheckConstraint(
            "temperature_c >= 25.0 AND temperature_c <= 45.0", name="temperature_in_range"
        ),
        CheckConstraint("pulse_bpm > 0", name="pulse_positive"),
        CheckConstraint("respiratory_rate > 0", name="respiratory_rate_positive"),
        CheckConstraint(
            "pain_score IS NULL OR (pain_score >= 0 AND pain_score <= 10)",
            name="pain_score_in_range",
        ),
    )
