"""SQLAlchemy ORM models for the Lab Orders module.

Two tables: `lab_orders` and `lab_order_items`. See
`app.modules.lab_orders.container` for the module's scope note.

`lab_orders.organization_id` carries a real foreign key to
`organizations.id`, `clinical_note_id` to `clinical_notes.id`,
`patient_id` to `patients.id`, `visit_id` to `patient_visits.id`, and
`doctor_id` to `doctors.id` — brand-new columns on a brand-new table, so
there is no backward-compatibility reason to defer them; none of
`organizations`, `clinical_notes`, `patients`, `patient_visits`,
`doctors`, `soap_notes`, or `prescriptions` is modified by this migration.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`/`prescriptions`' own choice for the
identical three columns: a lab order has no independent lifecycle meaning
without its clinical note. `doctor_id` (required) uses `ON DELETE
RESTRICT`, also matching those two tables' own `doctor_id`.

Unlike `soap_notes.clinical_note_id`/`prescriptions.clinical_note_id`,
`lab_orders.clinical_note_id` carries **no** unique index — "One Clinical
Note may contain multiple Lab Orders" (this task's own Business Rules),
the same one-to-many shape `clinical_notes.visit_id` itself has relative
to `patient_visits`. It still gets a plain index for
`list_lab_orders_for_clinical_note` query performance.

"order_number is globally unique" is enforced by a partial unique index
on `order_number WHERE deleted_at IS NULL`, the same shape
`prescriptions.prescription_number` already uses.

`lab_order_items.lab_order_id` uses `ON DELETE CASCADE`: "Lab Order Items
cannot exist without a Lab Order" is a hard existence dependency, so a
deleted lab order's items must not survive as orphans. `lab_order_items`
carries no `organization_id` column (this task's own field list never
lists one; tenant scoping is inherited transitively via
`lab_order_id -> lab_orders.organization_id`) and no `deleted_at` column
either (only "timestamps"/"audit fields" are listed for `LabOrderItem`,
the same asymmetry `prescription_items` already has).

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"Ordered Lab Orders must contain at least one Lab Order Item": a `CHECK`
constraint can only see this table's own row, never count rows in a
different table — that invariant is enforced exclusively at the
application layer (`application/use_cases/place_lab_order.py`).
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
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority

_priority_enum = pg_enum(Priority, "lab_order_priority_enum")
_lab_order_status_enum = pg_enum(LabOrderStatus, "lab_order_status_enum")


class LabOrderModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "lab_orders"

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
    order_number: Mapped[str] = mapped_column(Text, nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(nullable=False)
    priority: Mapped[Priority] = mapped_column(
        _priority_enum, nullable=False, default=Priority.ROUTINE
    )
    status: Mapped[LabOrderStatus] = mapped_column(
        _lab_order_status_enum, nullable=False, default=LabOrderStatus.DRAFT
    )
    clinical_information: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_lab_orders_order_number",
            "order_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_lab_orders_organization_id", "organization_id"),
        Index("ix_lab_orders_clinical_note_id", "clinical_note_id"),
        Index("ix_lab_orders_patient_id", "patient_id"),
        Index("ix_lab_orders_visit_id", "visit_id"),
        Index("ix_lab_orders_doctor_id", "doctor_id"),
    )


class LabOrderItemModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditActorMixin):
    __tablename__ = "lab_order_items"

    lab_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False
    )
    test_code: Mapped[str] = mapped_column(Text, nullable=False)
    test_name: Mapped[str] = mapped_column(Text, nullable=False)
    specimen_type: Mapped[str] = mapped_column(Text, nullable=False)
    specimen_site: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[LabOrderStatus] = mapped_column(
        _lab_order_status_enum, nullable=False, default=LabOrderStatus.DRAFT
    )
    instructions: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (Index("ix_lab_order_items_lab_order_id", "lab_order_id"),)
