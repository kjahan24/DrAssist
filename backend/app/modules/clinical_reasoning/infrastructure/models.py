"""SQLAlchemy ORM model for the Clinical Reasoning module.

One table: `clinical_reasoning`. See
`app.modules.clinical_reasoning.container` for the module's scope note.

`organization_id` carries a real foreign key to `organizations.id`,
`clinical_note_id` to `clinical_notes.id`, `patient_id` to `patients.id`,
`visit_id` to `patient_visits.id`, and `doctor_id` to `doctors.id` —
brand-new columns on a brand-new table, so there is no backward-
compatibility reason to defer them; none of `organizations`,
`clinical_notes`, `patients`, `patient_visits`, `doctors`, `soap_notes`,
`prescriptions`, `lab_orders`, or `lab_results` is modified by this
migration.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`/`prescriptions`/`lab_orders`' own choice
for the identical parent-reference shape: a reasoning record has no
independent lifecycle meaning without its clinical note. `doctor_id`
(required) uses `ON DELETE RESTRICT`, matching every other module's
`doctor_id`.

Unlike `soap_notes.clinical_note_id`/`prescriptions.clinical_note_id`,
`clinical_reasoning.clinical_note_id` carries **no** unique index — "One
Clinical Note may contain multiple Clinical Reasoning records" (this
task's own Business Rules), the same one-to-many shape
`lab_orders.clinical_note_id` already has. It still gets a plain index
for `list_clinical_reasoning_for_clinical_note` query performance.

No globally-unique "number" column exists on this table at all — this
task's own field list, unlike every other child-document module's, names
no such field (no `result_number`/`order_number`/`prescription_number`
equivalent), so there is no partial unique index to create here.

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"Approved/Rejected reasoning becomes immutable": a `CHECK` constraint
validates column *values* on write, not "can this row still be updated at
all" — that invariant is enforced exclusively at the application layer
(`ClinicalReasoning.ensure_editable()`), the same treatment
`app.modules.prescriptions.infrastructure.models` gives `Prescription`'s
own Draft/Final immutability (no CHECK constraint enforces that one
either, for the identical reason: it is not a column-value constraint).
"""

import uuid

from sqlalchemy import Float, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus

_reasoning_source_enum = pg_enum(ReasoningSource, "reasoning_source_enum")
_review_status_enum = pg_enum(ReviewStatus, "review_status_enum")


class ClinicalReasoningModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "clinical_reasoning"

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
    reasoning_source: Mapped[ReasoningSource] = mapped_column(
        _reasoning_source_enum, nullable=False
    )
    reasoning_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(_review_status_enum, nullable=False)
    reviewed_by_doctor: Mapped[bool] = mapped_column(nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=None)

    __table_args__ = (
        Index("ix_clinical_reasoning_organization_id", "organization_id"),
        Index("ix_clinical_reasoning_clinical_note_id", "clinical_note_id"),
        Index("ix_clinical_reasoning_patient_id", "patient_id"),
        Index("ix_clinical_reasoning_visit_id", "visit_id"),
        Index("ix_clinical_reasoning_doctor_id", "doctor_id"),
    )
