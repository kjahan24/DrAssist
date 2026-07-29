"""SQLAlchemy ORM model for the ICD-10 Coding module.

One table: `icd10_codes`. See `app.modules.icd10_coding.container` for
the module's scope note.

`organization_id` carries a real foreign key to `organizations.id`,
`clinical_note_id` to `clinical_notes.id`, `differential_diagnosis_id`
(nullable) to `differential_diagnoses.id`, `patient_id` to
`patients.id`, `visit_id` to `patient_visits.id`, and `doctor_id` to
`doctors.id` — brand-new columns on a brand-new table, so there is no
backward-compatibility reason to defer them; none of `organizations`,
`clinical_notes`, `differential_diagnoses`, `patients`, `patient_visits`,
or `doctors` is modified by this migration.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `differential_diagnoses`/`clinical_reasoning`'s own
choice for the identical parent-reference shape. `doctor_id` (required)
uses `ON DELETE RESTRICT`, matching every other module's `doctor_id`.

`differential_diagnosis_id` (nullable) uses `ON DELETE SET NULL`: it is
an optional cross-reference to a peer document, not an ownership
relationship, so a hard-deleted `differential_diagnoses` row should clear
this link rather than cascading the deletion or blocking it — the same
treatment `differential_diagnoses.clinical_reasoning_id` already
receives.

"Duplicate ICD-10 prevention within a Clinical Note" is enforced by a
partial unique index on `(clinical_note_id, icd10_code) WHERE deleted_at
IS NULL`. Unlike `differential_diagnoses.diagnosis_name` (free text,
de-duplicated case-insensitively only at the application layer, since no
functional index was requested), this works at the *database* level
because `ICD10Coding.__post_init__` normalizes `icd10_code` to uppercase
first — see `domain/entities.py` for the full reasoning. Following the
same precedent `visit_diagnoses`' own composite unique index already
established, there is no *separate* plain index on `clinical_note_id`
alone, since it is already this composite index's leading column.

"Only one ICD-10 code can be marked as Primary" is enforced by a partial
unique index on `clinical_note_id WHERE primary_code = true AND
deleted_at IS NULL`, the same shape `visit_diagnoses`' own
"one Primary diagnosis per Visit" index already uses.

Unlike `clinical_notes`, there is **no** `CHECK` constraint enforcing
"Approved and Rejected codes become read-only" (an editability concept,
not a column-value constraint) or "if linked to Differential Diagnosis,
both must belong to the same Clinical Note" (a cross-table invariant no
`CHECK` constraint can express) — both are enforced exclusively at the
application layer.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus

_coding_source_enum = pg_enum(CodingSource, "icd10_coding_source_enum")
_review_status_enum = pg_enum(ReviewStatus, "icd10_coding_review_status_enum")


class ICD10CodingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "icd10_codes"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    clinical_note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_notes.id", ondelete="CASCADE"), nullable=False
    )
    differential_diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("differential_diagnoses.id", ondelete="SET NULL"), default=None
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
    icd10_code: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis_title: Mapped[str] = mapped_column(Text, nullable=False)
    coding_source: Mapped[CodingSource] = mapped_column(_coding_source_enum, nullable=False)
    primary_code: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[ReviewStatus] = mapped_column(_review_status_enum, nullable=False)
    coding_notes: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_icd10_codes_clinical_note_id_icd10_code",
            "clinical_note_id",
            "icd10_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_icd10_codes_primary_per_clinical_note",
            "clinical_note_id",
            unique=True,
            postgresql_where=text("primary_code = true AND deleted_at IS NULL"),
        ),
        Index("ix_icd10_codes_organization_id", "organization_id"),
        Index("ix_icd10_codes_differential_diagnosis_id", "differential_diagnosis_id"),
        Index("ix_icd10_codes_patient_id", "patient_id"),
        Index("ix_icd10_codes_visit_id", "visit_id"),
        Index("ix_icd10_codes_doctor_id", "doctor_id"),
    )
