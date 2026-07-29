"""SQLAlchemy ORM models for the Prescription module.

Two tables: `prescriptions` and `prescription_items`. See
`app.modules.prescriptions.container` for the module's scope note.

`prescriptions.organization_id` carries a real foreign key to
`organizations.id`, `clinical_note_id` to `clinical_notes.id`,
`patient_id` to `patients.id`, `visit_id` to `patient_visits.id`, and
`doctor_id` to `doctors.id` — brand-new columns on a brand-new table, so
there is no backward-compatibility reason to defer them; none of
`organizations`, `clinical_notes`, `patients`, `patient_visits`, or
`doctors` is modified by this migration.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`' own choice for the identical three
columns (see that model's own comment): a prescription has no
independent lifecycle meaning without its clinical note, and
`patient_id`/`visit_id` are derived copies of `clinical_notes`' own
columns. `doctor_id` (required) uses `ON DELETE RESTRICT`, also matching
`soap_notes.doctor_id`.

"One Clinical Note can have at most one Prescription" is enforced by a
partial unique index on `clinical_note_id WHERE deleted_at IS NULL`, the
same one-to-one shape `soap_notes.clinical_note_id` already uses.
"`prescription_number` is globally unique" is enforced by a partial
unique index on `prescription_number WHERE deleted_at IS NULL`, the same
shape `clinical_notes.note_number` already uses.

`prescription_items.prescription_id` uses `ON DELETE CASCADE`:
"Prescription Items cannot exist without a Prescription" (this task's own
Business Rules) is a hard existence dependency, not merely a lifecycle
preference, so a deleted prescription's items must not survive as
orphans. `prescription_items` carries no `organization_id` — this task's
own field list for `PrescriptionItem` never lists one; tenant scoping is
inherited transitively via `prescription_id -> prescriptions
.organization_id`, and inventing an extra column no business rule asks
for would be scope creep.

`prescription_items` also carries no `deleted_at` — unlike every other
table in this schema, this task's own field list gives `Prescription`
"soft delete" but omits it for `PrescriptionItem` (only "timestamps" and
"audit fields" are listed), so `PrescriptionItemModel` uses only
`TimestampMixin`/`AuditActorMixin`, not `SoftDeleteMixin`.

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"a Final Prescription must contain at least one Prescription Item": a
`CHECK` constraint can only see this table's own row, never count rows in
a *different* table (`prescription_items`) — that invariant is enforced
exclusively at the application layer
(`application/use_cases/finalize_prescription.py`), the same kind of
documented, deliberate gap `soap_notes`' own "read-only when Signed/Locked"
invariant already has.
"""

import uuid
from datetime import date

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.prescriptions.domain.enums import AdministrationRoute, PrescriptionStatus

_prescription_status_enum = pg_enum(PrescriptionStatus, "prescription_status_enum")
_administration_route_enum = pg_enum(AdministrationRoute, "administration_route_enum")


class PrescriptionModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "prescriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    clinical_note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_notes.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    prescription_number: Mapped[str] = mapped_column(Text, nullable=False)
    prescription_date: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[PrescriptionStatus] = mapped_column(
        _prescription_status_enum, nullable=False, default=PrescriptionStatus.DRAFT
    )
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_prescriptions_clinical_note_id",
            "clinical_note_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_prescriptions_prescription_number",
            "prescription_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_prescriptions_organization_id", "organization_id"),
        Index("ix_prescriptions_patient_id", "patient_id"),
        Index("ix_prescriptions_visit_id", "visit_id"),
        Index("ix_prescriptions_doctor_id", "doctor_id"),
    )


class PrescriptionItemModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditActorMixin):
    __tablename__ = "prescription_items"

    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False
    )
    medication_name: Mapped[str] = mapped_column(Text, nullable=False)
    generic_name: Mapped[str | None] = mapped_column(Text, default=None)
    strength: Mapped[str] = mapped_column(Text, nullable=False)
    dosage: Mapped[str] = mapped_column(Text, nullable=False)
    dosage_unit: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[AdministrationRoute] = mapped_column(_administration_route_enum, nullable=False)
    duration: Mapped[str] = mapped_column(Text, nullable=False)
    duration_unit: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (Index("ix_prescription_items_prescription_id", "prescription_id"),)
