"""SQLAlchemy ORM model for the Differential Diagnosis module.

One table: `differential_diagnoses`. See
`app.modules.differential_diagnosis.container` for the module's scope
note.

`organization_id` carries a real foreign key to `organizations.id`,
`clinical_note_id` to `clinical_notes.id`, `patient_id` to `patients.id`,
`visit_id` to `patient_visits.id`, and `doctor_id` to `doctors.id` —
brand-new columns on a brand-new table, so there is no backward-
compatibility reason to defer them; none of `organizations`,
`clinical_notes`, `patients`, `patient_visits`, `doctors`,
`clinical_reasoning`, or any other prior table is modified by this
migration.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `clinical_reasoning`/`lab_orders`' own choice for the
identical parent-reference shape. `doctor_id` (required) uses `ON DELETE
RESTRICT`, matching every other module's `doctor_id`.

`clinical_reasoning_id` (nullable) uses `ON DELETE SET NULL`: unlike the
required parent-reference columns above, this is an optional cross-
reference to a peer document, not an ownership relationship — a
differential diagnosis has independent lifecycle meaning with or without
a linked reasoning record, so a hard-deleted `clinical_reasoning` row
should simply clear this link rather than cascading the deletion or
blocking it, the same treatment `visit_chief_complaints.recorded_by`/
`visit_diagnoses.diagnosed_by` already give their own optional,
non-owning doctor references.

"Ranking must be unique within a Clinical Note" is enforced by a partial
unique index on `(clinical_note_id, ranking) WHERE deleted_at IS NULL`,
the same shape `visit_diagnoses`' own `sequence_number` uniqueness
already uses — and, following that same precedent, there is no *separate*
plain index on `clinical_note_id` alone, since it is already the leading
column of this composite index. `ranking >= 1` is additionally enforced
as a `CHECK` constraint (defense-in-depth alongside
`DifferentialDiagnosis.__post_init__`), the same treatment
`visit_diagnoses.sequence_number` already receives.

"Duplicate diagnosis prevention" (diagnosis_name uniqueness within a
Clinical Note) has **no** database-level enforcement: matching is
case-insensitive (this task's own Validation section does not specify
collation-level case folding, and a `CHECK`/unique index cannot express
"case-insensitively unique" without a functional index this task never
asked for) — it is enforced exclusively at the application layer
(`application/use_cases/create_differential_diagnosis.py`).

Unlike `clinical_notes`, there is **no** `CHECK` constraint enforcing
"Approved and Rejected diagnoses become read-only" (an editability
concept, not a column-value constraint) or "if linked to Clinical
Reasoning, both records must belong to the same Clinical Note" (a
cross-table invariant a `CHECK` constraint cannot express) — both are
enforced exclusively at the application layer.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus

_diagnosis_source_enum = pg_enum(DiagnosisSource, "differential_diagnosis_source_enum")
_review_status_enum = pg_enum(ReviewStatus, "differential_diagnosis_review_status_enum")


class DifferentialDiagnosisModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "differential_diagnoses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    clinical_note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_notes.id", ondelete="CASCADE"), nullable=False
    )
    clinical_reasoning_id: Mapped[uuid.UUID | None] = mapped_column(
        # Explicit `name=` because the naming-convention-derived default
        # (`fk_differential_diagnoses_clinical_reasoning_id_clinical_reasoning`,
        # 66 bytes) exceeds Postgres's 63-byte NAMEDATALEN limit — must
        # match the shortened name the migration actually creates.
        ForeignKey(
            "clinical_reasoning.id",
            ondelete="SET NULL",
            name="fk_differential_diagnoses_clinical_reasoning_id",
        ),
        default=None,
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
    diagnosis_name: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis_source: Mapped[DiagnosisSource] = mapped_column(
        _diagnosis_source_enum, nullable=False
    )
    ranking: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(_review_status_enum, nullable=False)
    likelihood_score: Mapped[float | None] = mapped_column(Float, default=None)
    supporting_evidence: Mapped[str | None] = mapped_column(Text, default=None)
    excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index(
            "uq_differential_diagnoses_clinical_note_id_ranking",
            "clinical_note_id",
            "ranking",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_differential_diagnoses_organization_id", "organization_id"),
        Index("ix_differential_diagnoses_clinical_reasoning_id", "clinical_reasoning_id"),
        Index("ix_differential_diagnoses_patient_id", "patient_id"),
        Index("ix_differential_diagnoses_visit_id", "visit_id"),
        Index("ix_differential_diagnoses_doctor_id", "doctor_id"),
        CheckConstraint("ranking >= 1", name="ranking_starts_at_one"),
    )
