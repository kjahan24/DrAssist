"""create lab orders tables

Creates the Lab Orders foundation schema: lab_orders and
lab_order_items.

`lab_orders.organization_id` references `organizations.id`,
`clinical_note_id` references `clinical_notes.id`, `patient_id`
references `patients.id`, `visit_id` references `patient_visits.id`, and
`doctor_id` references `doctors.id` (all chained before this migration) —
this is why this migration's `down_revision` chains after the
Prescriptions migration, not a modification to any prior module's
tables. No column is added to, or constraint changed on,
`organizations`/`clinical_notes`/`patients`/`patient_visits`/`doctors`/
`soap_notes`/`prescriptions`/`users`/any other prior table here.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`/`prescriptions`' own choice for the
identical three columns. `doctor_id` (required) uses `ON DELETE
RESTRICT`, also matching those two tables' own `doctor_id`.

Unlike `soap_notes.clinical_note_id`/`prescriptions.clinical_note_id`,
`lab_orders.clinical_note_id` carries **no** unique index — "One Clinical
Note may contain multiple Lab Orders" (this task's own Business Rules),
the same one-to-many shape `clinical_notes.visit_id` itself has. It still
gets a plain index for `list_lab_orders_for_clinical_note` query
performance.

"order_number is globally unique" is enforced by a partial unique index
on `order_number WHERE deleted_at IS NULL`, the same shape
`prescriptions.prescription_number` already uses.

`lab_order_items.lab_order_id` uses `ON DELETE CASCADE`: "Lab Order Items
cannot exist without a Lab Order" is a hard existence dependency.
`lab_order_items` carries no `organization_id` column and no `deleted_at`
column — this task's own field list for `LabOrderItem` lists neither
(tenant scoping is inherited transitively via
`lab_order_id -> lab_orders.organization_id`, and only
"timestamps"/"audit fields" are listed, not "soft delete") — see
`LabOrderItemModel`'s own comment for the full reasoning. `status` on
`lab_order_items` reuses the same `lab_order_status_enum` Postgres type as
`lab_orders.status` — see `LabOrderModel`'s own module docstring for why
one status enum covers both entities.

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"Ordered Lab Orders must contain at least one Lab Order Item": a `CHECK`
constraint can only see this table's own row, never count rows in a
different table — that invariant is enforced exclusively at the
application layer (`application/use_cases/place_lab_order.py`).

Revision ID: 5fb92660855d
Revises: d7b7f088c9c3
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5fb92660855d"
down_revision: str | None = "d7b7f088c9c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def _audit_columns() -> list[sa.Column]:
    """The five standard columns every soft-deletable table in this schema
    carries, minus `id` (added separately since its type/default is
    identical everywhere but declared first). See
    `docs/database/00_overview.md`.
    """
    return [
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("deleted_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def _audit_columns_no_soft_delete() -> list[sa.Column]:
    """`lab_order_items` omits `deleted_at` — see this migration's own
    module docstring for why."""
    return [
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def _audit_fks(table: str) -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=f"fk_{table}_created_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=f"fk_{table}_updated_by_users", ondelete="SET NULL"
        ),
    ]


def upgrade() -> None:
    priority_enum = postgresql.ENUM(
        "routine",
        "urgent",
        "stat",
        name="lab_order_priority_enum",
        create_type=False,
    )
    priority_enum.create(op.get_bind(), checkfirst=True)

    lab_order_status_enum = postgresql.ENUM(
        "draft",
        "ordered",
        "collected",
        "cancelled",
        name="lab_order_status_enum",
        create_type=False,
    )
    lab_order_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lab_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_number", sa.Text(), nullable=False),
        sa.Column("ordered_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("priority", priority_enum, nullable=False, server_default="routine"),
        sa.Column("status", lab_order_status_enum, nullable=False, server_default="draft"),
        sa.Column("clinical_information", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_lab_orders"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_lab_orders_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_note_id"],
            ["clinical_notes.id"],
            name="fk_lab_orders_clinical_note_id_clinical_notes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_lab_orders_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_lab_orders_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_lab_orders_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("lab_orders"),
    )
    op.create_index(
        "uq_lab_orders_order_number",
        "lab_orders",
        ["order_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_lab_orders_organization_id", "lab_orders", ["organization_id"])
    op.create_index("ix_lab_orders_clinical_note_id", "lab_orders", ["clinical_note_id"])
    op.create_index("ix_lab_orders_patient_id", "lab_orders", ["patient_id"])
    op.create_index("ix_lab_orders_visit_id", "lab_orders", ["visit_id"])
    op.create_index("ix_lab_orders_doctor_id", "lab_orders", ["doctor_id"])

    op.create_table(
        "lab_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_code", sa.Text(), nullable=False),
        sa.Column("test_name", sa.Text(), nullable=False),
        sa.Column("specimen_type", sa.Text(), nullable=False),
        sa.Column("specimen_site", sa.Text(), nullable=True),
        sa.Column("status", lab_order_status_enum, nullable=False, server_default="draft"),
        sa.Column("instructions", sa.Text(), nullable=True),
        *_audit_columns_no_soft_delete(),
        sa.PrimaryKeyConstraint("id", name="pk_lab_order_items"),
        sa.ForeignKeyConstraint(
            ["lab_order_id"],
            ["lab_orders.id"],
            name="fk_lab_order_items_lab_order_id_lab_orders",
            ondelete="CASCADE",
        ),
        *_audit_fks("lab_order_items"),
    )
    op.create_index("ix_lab_order_items_lab_order_id", "lab_order_items", ["lab_order_id"])


def downgrade() -> None:
    op.drop_table("lab_order_items")
    op.drop_table("lab_orders")

    postgresql.ENUM(name="lab_order_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="lab_order_priority_enum").drop(op.get_bind(), checkfirst=True)
