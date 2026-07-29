"""SQLAlchemy ORM models for the Lab Results module.

Two tables: `lab_results` and `lab_result_items`. See
`app.modules.lab_results.container` for the module's scope note.

`lab_results.organization_id` carries a real foreign key to
`organizations.id`, `lab_order_id` to `lab_orders.id`, `patient_id` to
`patients.id`, `visit_id` to `patient_visits.id`, and `doctor_id` to
`doctors.id` — brand-new columns on a brand-new table, so there is no
backward-compatibility reason to defer them; none of `organizations`,
`lab_orders`, `patients`, `patient_visits`, `doctors`, `clinical_notes`,
`soap_notes`, or `prescriptions` is modified by this migration.

`lab_order_id` uses `ON DELETE CASCADE`, matching `soap_notes`/
`prescriptions`' own choice for their equivalent parent-reference column:
a lab result has no independent lifecycle meaning without its lab order.
`patient_id`/`visit_id` similarly use `ON DELETE CASCADE` (derived copies
of the parent's own columns); `doctor_id` (required) uses `ON DELETE
RESTRICT`, matching every other module's `doctor_id`.

"One Lab Order may have at most one Lab Result" is enforced by a partial
unique index on `lab_order_id WHERE deleted_at IS NULL`, the same
one-to-one shape `soap_notes.clinical_note_id`/`prescriptions
.clinical_note_id` already use. "result_number is globally unique" is
enforced by a partial unique index on `result_number WHERE deleted_at IS
NULL`, the same shape `prescriptions.prescription_number` already uses.

`lab_result_items.lab_result_id` uses `ON DELETE CASCADE`: "Lab Result
Items cannot exist without a Lab Result" is a hard existence dependency.
`lab_result_items.lab_order_item_id` — the FK backing "Every Lab Result
Item must reference an existing Lab Order Item" — uses `ON DELETE
RESTRICT` instead: unlike every other item-to-parent reference in this
schema, a `lab_order_items` row is reference data a *result* is reporting
against, not a row this table owns the lifecycle of; silently cascading a
deletion into destroyed result data would be a healthcare-data-integrity
hazard, so deleting a `lab_order_items` row that already has a reported
result is blocked instead, the same reasoning every `doctor_id` column in
this schema already applies to protect clinical attribution data.

`lab_result_items` carries no `organization_id` column (this task's own
field list never lists one; tenant scoping is inherited transitively via
`lab_result_id -> lab_results.organization_id`) and no `deleted_at`
column either (only "timestamps"/"audit fields" are listed for
`LabResultItem`, the same asymmetry `prescription_items`/
`lab_order_items` already have).

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"A Final Lab Result must contain at least one Lab Result Item": a `CHECK`
constraint can only see this table's own row, never count rows in a
different table — that invariant is enforced exclusively at the
application layer (`application/use_cases/finalize_lab_result.py`).
"""

import uuid
from datetime import datetime

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
from app.modules.lab_results.domain.enums import AbnormalFlag, LabResultStatus

_lab_result_status_enum = pg_enum(LabResultStatus, "lab_result_status_enum")
_abnormal_flag_enum = pg_enum(AbnormalFlag, "abnormal_flag_enum")


class LabResultModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "lab_results"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    lab_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False
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
    result_number: Mapped[str] = mapped_column(Text, nullable=False)
    reported_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[LabResultStatus] = mapped_column(
        _lab_result_status_enum, nullable=False, default=LabResultStatus.DRAFT
    )
    laboratory_name: Mapped[str | None] = mapped_column(Text, default=None)
    comments: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_lab_results_lab_order_id",
            "lab_order_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_lab_results_result_number",
            "result_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_lab_results_organization_id", "organization_id"),
        Index("ix_lab_results_patient_id", "patient_id"),
        Index("ix_lab_results_visit_id", "visit_id"),
        Index("ix_lab_results_doctor_id", "doctor_id"),
    )


class LabResultItemModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditActorMixin):
    __tablename__ = "lab_result_items"

    lab_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_results.id", ondelete="CASCADE"), nullable=False
    )
    lab_order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_order_items.id", ondelete="RESTRICT"), nullable=False
    )
    test_code: Mapped[str] = mapped_column(Text, nullable=False)
    test_name: Mapped[str] = mapped_column(Text, nullable=False)
    result_value: Mapped[str] = mapped_column(Text, nullable=False)
    result_unit: Mapped[str | None] = mapped_column(Text, default=None)
    reference_range: Mapped[str | None] = mapped_column(Text, default=None)
    abnormal_flag: Mapped[AbnormalFlag] = mapped_column(_abnormal_flag_enum, nullable=False)
    interpretation: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index("ix_lab_result_items_lab_result_id", "lab_result_id"),
        Index("ix_lab_result_items_lab_order_item_id", "lab_order_item_id"),
    )
