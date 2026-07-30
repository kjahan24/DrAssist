"""SQLAlchemy ORM model for the Doctor Review module.

One table: `doctor_reviews`. See `app.modules.doctor_review.container`
for the module's scope note.

`organization_id` carries a real foreign key to `organizations.id`,
`patient_id` to `patients.id`, `visit_id` to `patient_visits.id`,
`doctor_id` to `doctors.id`, and `clinical_note_id` to
`clinical_notes.id` — brand-new columns on a brand-new table, so there is
no backward-compatibility reason to defer them; none of `organizations`,
`patients`, `patient_visits`, `doctors`, or `clinical_notes` is modified
by this migration.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`/`icd10_codes`'s own choice for the
identical parent-reference shape. `doctor_id` (required) uses `ON DELETE
RESTRICT`, matching every other module's `doctor_id`.

"One Clinical Note has exactly zero or one Doctor Review" is enforced by
a partial unique index on `clinical_note_id WHERE deleted_at IS NULL`,
the same one-to-one shape `soap_notes.clinical_note_id` already uses.

There is no `CHECK` constraint here: "Review status transitions must be
validated" is enforced exclusively by `DoctorReview._transition_to()`'s
own transition map (a `CHECK` constraint can only see this table's own
row, never the *previous* value of `review_status`, so it cannot express
a transition rule), and "Cross-module consistency" for the `approved_*`
columns is a cross-*table* invariant no `CHECK` constraint can express
either — both are enforced exclusively at the application layer.
"""

import uuid
from datetime import datetime

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
from app.modules.doctor_review.domain.enums import ReviewStatus

_review_status_enum = pg_enum(ReviewStatus, "doctor_review_status_enum")


class DoctorReviewModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "doctor_reviews"

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
    clinical_note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_notes.id", ondelete="CASCADE"), nullable=False
    )
    review_status: Mapped[ReviewStatus] = mapped_column(_review_status_enum, nullable=False)
    review_comment: Mapped[str | None] = mapped_column(Text, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    approved_clinical_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_soap_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_prescription: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_lab_orders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_lab_results: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_reasoning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_differential_diagnosis: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    approved_icd10: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index(
            "uq_doctor_reviews_clinical_note_id",
            "clinical_note_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_doctor_reviews_organization_id", "organization_id"),
        Index("ix_doctor_reviews_patient_id", "patient_id"),
        Index("ix_doctor_reviews_visit_id", "visit_id"),
        Index("ix_doctor_reviews_doctor_id", "doctor_id"),
    )
