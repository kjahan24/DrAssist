"""SQLAlchemy ORM model for the SOAP Notes module.

One table: `soap_notes`. See `app.modules.soap_notes.container` for the
module's scope note.

`soap_notes.organization_id` carries a real foreign key to
`organizations.id`, `clinical_note_id` to `clinical_notes.id`,
`patient_id` to `patients.id`, `visit_id` to `patient_visits.id`, and
`doctor_id` to `doctors.id` — brand-new columns on a brand-new table, so
there is no backward-compatibility reason to defer them; none of
`organizations`, `clinical_notes`, `patients`, `patient_visits`, or
`doctors` is modified by this migration.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`: a SOAP note has no independent lifecycle meaning without its
clinical note (matching `visit_procedures.visit_id`'s own reasoning), and
`patient_id`/`visit_id` mirror `clinical_notes.patient_id`/`visit_id`'s
own CASCADE choice, since they're derived copies of exactly those
columns (see `SOAPNote`'s own docstring for why they're never
independently supplied). `doctor_id` (required) uses `ON DELETE
RESTRICT`, matching `clinical_notes.doctor_id`.

"One Clinical Note can have at most one SOAP Note" is enforced by a
partial unique index on `clinical_note_id WHERE deleted_at IS NULL`, the
same one-to-one shape `doctor_profiles.doctor_id` and
`visit_vital_signs.visit_id` already use.

Unlike every prior module, there is **no** `CHECK` constraint here
enforcing "read-only when the linked Clinical Note is Signed/Locked": a
`CHECK` constraint can only see this table's own row, never
`clinical_notes.status` in another table — see `SOAPNote`'s own
docstring for the full reasoning. That invariant is enforced exclusively
at the application layer (`application/use_cases/update_soap_note.py`).
"""

import uuid

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class SOAPNoteModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "soap_notes"

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
    chief_complaint: Mapped[str | None] = mapped_column(Text, default=None)
    history_of_present_illness: Mapped[str | None] = mapped_column(Text, default=None)
    review_of_systems: Mapped[str | None] = mapped_column(Text, default=None)
    physical_examination: Mapped[str | None] = mapped_column(Text, default=None)
    vital_sign_summary: Mapped[str | None] = mapped_column(Text, default=None)
    assessment: Mapped[str | None] = mapped_column(Text, default=None)
    plan: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_soap_notes_clinical_note_id",
            "clinical_note_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_soap_notes_organization_id", "organization_id"),
        Index("ix_soap_notes_patient_id", "patient_id"),
        Index("ix_soap_notes_visit_id", "visit_id"),
        Index("ix_soap_notes_doctor_id", "doctor_id"),
    )
