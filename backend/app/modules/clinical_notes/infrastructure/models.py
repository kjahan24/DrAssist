"""SQLAlchemy ORM model for the Clinical Notes module.

One table: `clinical_notes`. See `app.modules.clinical_notes.container`
for the module's scope note — this table is the master record every
future clinical document module will add its own `clinical_note_id` FK
to; nothing here needs to change to support that.

`clinical_notes.organization_id` carries a real foreign key to
`organizations.id`, `patient_id` to `patients.id`, `visit_id` to
`patient_visits.id`, and `doctor_id`/`signed_by` to `doctors.id` —
brand-new columns on a brand-new table, so there is no
backward-compatibility reason to defer them; none of `organizations`,
`patients`, `patient_visits`, or `doctors` is modified by this migration.

`patient_id` and `visit_id` use `ON DELETE CASCADE`, matching
`patient_visits.patient_id`'s and `visit_attachments.visit_id`'s own
choices respectively: a clinical note has no independent lifecycle
meaning without either. `doctor_id` (the required authoring doctor) uses
`ON DELETE RESTRICT`, matching `patient_visits.doctor_id` — a `NOT NULL`
column cannot use `SET NULL`, and `CASCADE` would silently destroy
documentation history if a doctor row were ever removed. `signed_by`
(nullable, best-effort attribution) uses `ON DELETE SET NULL`, matching
`visit_attachments.uploaded_by`.

`note_number` is globally unique (partial index `WHERE deleted_at IS
NULL`) — matching the unqualified "must be globally unique" wording in
this task's business rules, the same shape
`visit_attachments.storage_key`/`checksum_sha256` already use.

`doctor_id` is indexed alongside `organization_id`/`patient_id`/
`visit_id`, unlike the nullable, best-effort `signed_by`/
`visit_attachments.uploaded_by`-style attribution columns this schema
otherwise leaves unindexed: it is a required, load-bearing identity
reference (the authoring doctor), the same shape as the other three
indexed FKs — and the explicitly future "Doctor Review" module (see
`app.modules.clinical_notes.container`'s scope note) is an obvious
consumer of "every note a given doctor authored".

Four business rules are enforced as DB `CHECK` constraints (in addition
to `ClinicalNote.__post_init__`, the same defense-in-depth pattern
applied to every prior module) — see that module's own docstring for the
full reasoning behind treating `locked_at` symmetrically with
`signed_at`/`signed_by` even though only the latter two are named
explicitly:
- "signed_at exists only when status = Signed or Locked" (both
  directions) -> `signed_requires_signature` / `unsigned_forbids_signature`.
- The same bidirectional shape for `locked_at` ->
  `locked_requires_locked_at` / `unlocked_forbids_locked_at`.
"""

import uuid
from datetime import datetime

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
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType

_clinical_note_type_enum = pg_enum(ClinicalNoteType, "clinical_note_type_enum")
_clinical_note_status_enum = pg_enum(ClinicalNoteStatus, "clinical_note_status_enum")


class ClinicalNoteModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "clinical_notes"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
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
    note_number: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[ClinicalNoteType] = mapped_column(_clinical_note_type_enum, nullable=False)
    status: Mapped[ClinicalNoteStatus] = mapped_column(
        _clinical_note_status_enum, nullable=False, default=ClinicalNoteStatus.DRAFT
    )
    encounter_datetime: Mapped[datetime] = mapped_column(nullable=False)
    chief_complaint_summary: Mapped[str | None] = mapped_column(Text, default=None)
    history_summary: Mapped[str | None] = mapped_column(Text, default=None)
    examination_summary: Mapped[str | None] = mapped_column(Text, default=None)
    assessment_summary: Mapped[str | None] = mapped_column(Text, default=None)
    plan_summary: Mapped[str | None] = mapped_column(Text, default=None)
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_model: Mapped[str | None] = mapped_column(Text, default=None)
    ai_version: Mapped[str | None] = mapped_column(Text, default=None)
    signed_at: Mapped[datetime | None] = mapped_column(default=None)
    signed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    locked_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_clinical_notes_note_number",
            "note_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_clinical_notes_organization_id", "organization_id"),
        Index("ix_clinical_notes_patient_id", "patient_id"),
        Index("ix_clinical_notes_visit_id", "visit_id"),
        Index("ix_clinical_notes_doctor_id", "doctor_id"),
        CheckConstraint(
            "status NOT IN ('signed', 'locked') OR "
            "(signed_at IS NOT NULL AND signed_by IS NOT NULL)",
            name="signed_requires_signature",
        ),
        CheckConstraint(
            "status IN ('signed', 'locked') OR (signed_at IS NULL AND signed_by IS NULL)",
            name="unsigned_forbids_signature",
        ),
        CheckConstraint(
            "status != 'locked' OR locked_at IS NOT NULL",
            name="locked_requires_locked_at",
        ),
        CheckConstraint(
            "status = 'locked' OR locked_at IS NULL",
            name="unlocked_forbids_locked_at",
        ),
    )
