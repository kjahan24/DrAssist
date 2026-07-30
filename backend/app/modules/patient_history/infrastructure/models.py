"""SQLAlchemy ORM model for the Patient History module.

One table: `patient_histories`. See
`app.modules.patient_history.container` for the module's scope note.

`organization_id` carries a real foreign key to `organizations.id`,
`patient_id` to `patients.id`, `visit_id` to `patient_visits.id`, and
`doctor_review_id` to `doctor_reviews.id` — brand-new columns on a
brand-new table, so there is no backward-compatibility reason to defer
them; none of `organizations`, `patients`, `patient_visits`, or
`doctor_reviews` is modified by this migration.

`patient_id` and `visit_id` use `ON DELETE CASCADE`, matching every
prior module's own choice for those two columns. `organization_id` uses
`ON DELETE RESTRICT`, matching every other module's `organization_id`.
`doctor_review_id` also uses `ON DELETE RESTRICT` — deliberately
*unlike* `icd10_codes.differential_diagnosis_id`/`differential_diagnoses
.clinical_reasoning_id` (both `SET NULL`, since those are optional
cross-references to a peer document): `doctor_review_id` here is
required, and `PatientHistory` is meant to be *more* durable than the
review that authorized it — "the patient's longitudinal Electronic
Medical Record" is the permanent copy. `RESTRICT` means a Doctor Review
can never be hard-deleted out from under history it already produced;
`CASCADE` would silently destroy permanent medical record entries, which
directly contradicts "History records are immutable" / "append-only".

`reference_id` carries **no** foreign key: `reference_type` names one of
eight different tables it points into (`clinical_notes`, `soap_notes`,
`prescriptions`, `lab_orders`, `lab_results`, `differential_diagnoses`,
`icd10_codes`, `doctor_reviews`), and Postgres cannot express a
polymorphic foreign key. "Reference validation" is therefore enforced
exclusively at the application layer, by
`PatientHistoryReferenceValidator`.

"Duplicate history records for the same source are prohibited" is
enforced by a partial unique index on `(reference_type, reference_id)
WHERE deleted_at IS NULL` — the composite key that actually identifies
"the same source", the same "normalize the natural key into a real
database constraint" precedent `icd10_codes`' own
`(clinical_note_id, icd10_code)` duplicate-prevention index sets.

`(patient_id, encounter_date)` is a composite index, not two separate
ones: it serves `list_by_patient` (patient_id as the leading column)
*and* the chronological-timeline ordering every stated Future
Compatibility consumer (Timeline View, Longitudinal EMR, FHIR Bundle,
Patient Portal, Mobile App) needs, in one index — the same "no separate
plain index on the leading column" precedent `differential_diagnoses`'
own composite unique index already sets.

There is no `CHECK` constraint here: nothing in this task's Business
Rules states a self-contained, column-value invariant a `CHECK` could
express — "only Approved Doctor Reviews may create Patient History" and
"Reference validation" both require reading another table (this one's
own `doctor_review_id` is not itself enough to know the *status* of that
review; that lookup is exactly what `CHECK` constraints cannot do), so
both are enforced exclusively at the application layer.
"""

import uuid
from datetime import date

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
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType

_history_type_enum = pg_enum(HistoryType, "patient_history_type_enum")
_reference_type_enum = pg_enum(ReferenceType, "patient_history_reference_type_enum")


class PatientHistoryModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "patient_histories"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    doctor_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctor_reviews.id", ondelete="RESTRICT"), nullable=False
    )
    history_type: Mapped[HistoryType] = mapped_column(_history_type_enum, nullable=False)
    reference_type: Mapped[ReferenceType] = mapped_column(_reference_type_enum, nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    encounter_date: Mapped[date] = mapped_column(nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_from_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index(
            "uq_patient_histories_reference_type_reference_id",
            "reference_type",
            "reference_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_patient_histories_patient_id_encounter_date", "patient_id", "encounter_date"),
        Index("ix_patient_histories_organization_id", "organization_id"),
        Index("ix_patient_histories_visit_id", "visit_id"),
        Index("ix_patient_histories_doctor_review_id", "doctor_review_id"),
    )
