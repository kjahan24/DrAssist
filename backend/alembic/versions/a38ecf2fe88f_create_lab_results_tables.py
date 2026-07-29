"""create lab results tables

Creates the Lab Results foundation schema: lab_results and
lab_result_items.

`lab_results.organization_id` references `organizations.id`,
`lab_order_id` references `lab_orders.id`, `patient_id` references
`patients.id`, `visit_id` references `patient_visits.id`, and
`doctor_id` references `doctors.id` (all chained before this migration)
— this is why this migration's `down_revision` chains after the Lab
Orders migration, not a modification to any prior module's tables. No
column is added to, or constraint changed on, `organizations`/
`lab_orders`/`patients`/`patient_visits`/`doctors`/`clinical_notes`/
`soap_notes`/`prescriptions`/`users`/any other prior table here.

`lab_order_id`, `patient_id`, and `visit_id` all use `ON DELETE CASCADE`,
matching `soap_notes`/`prescriptions`' own choice for the identical
parent-reference shape: a lab result has no independent lifecycle meaning
without its lab order. `doctor_id` (required) uses `ON DELETE RESTRICT`,
matching every other module's `doctor_id`.

"One Lab Order may have at most one Lab Result" is enforced by a partial
unique index on `lab_order_id WHERE deleted_at IS NULL`, the same
one-to-one shape `soap_notes.clinical_note_id`/`prescriptions
.clinical_note_id` already use. "result_number is globally unique" is
enforced by a partial unique index on `result_number WHERE deleted_at IS
NULL`, the same shape `prescriptions.prescription_number` already uses.

`lab_result_items.lab_result_id` uses `ON DELETE CASCADE`: "Lab Result
Items cannot exist without a Lab Result" is a hard existence dependency.
`lab_result_items.lab_order_item_id` — backing "Every Lab Result Item
must reference an existing Lab Order Item" — uses `ON DELETE RESTRICT`
instead: a `lab_order_items` row is reference data a result is reporting
against, not a row this table owns the lifecycle of, so deleting a
`lab_order_items` row that already has a reported result is blocked
rather than silently cascading the result data away — see
`LabResultItemModel`'s own comment for the full reasoning.

`lab_result_items` carries no `organization_id` column and no
`deleted_at` column — this task's own field list for `LabResultItem`
lists neither (tenant scoping is inherited transitively via
`lab_result_id -> lab_results.organization_id`, and only
"timestamps"/"audit fields" are listed, not "soft delete") — the same
asymmetry `prescription_items`/`lab_order_items` already have.

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"A Final Lab Result must contain at least one Lab Result Item": a `CHECK`
constraint can only see this table's own row, never count rows in a
different table — that invariant is enforced exclusively at the
application layer (`application/use_cases/finalize_lab_result.py`).

Revision ID: a38ecf2fe88f
Revises: 5fb92660855d
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a38ecf2fe88f"
down_revision: str | None = "5fb92660855d"
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
    """`lab_result_items` omits `deleted_at` — see this migration's own
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
    lab_result_status_enum = postgresql.ENUM(
        "draft",
        "final",
        name="lab_result_status_enum",
        create_type=False,
    )
    lab_result_status_enum.create(op.get_bind(), checkfirst=True)

    abnormal_flag_enum = postgresql.ENUM(
        "normal",
        "low",
        "high",
        "critical",
        "abnormal",
        name="abnormal_flag_enum",
        create_type=False,
    )
    abnormal_flag_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lab_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_number", sa.Text(), nullable=False),
        sa.Column("reported_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("status", lab_result_status_enum, nullable=False, server_default="draft"),
        sa.Column("laboratory_name", sa.Text(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_lab_results"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_lab_results_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lab_order_id"],
            ["lab_orders.id"],
            name="fk_lab_results_lab_order_id_lab_orders",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_lab_results_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_lab_results_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_lab_results_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("lab_results"),
    )
    op.create_index(
        "uq_lab_results_lab_order_id",
        "lab_results",
        ["lab_order_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_lab_results_result_number",
        "lab_results",
        ["result_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_lab_results_organization_id", "lab_results", ["organization_id"])
    op.create_index("ix_lab_results_patient_id", "lab_results", ["patient_id"])
    op.create_index("ix_lab_results_visit_id", "lab_results", ["visit_id"])
    op.create_index("ix_lab_results_doctor_id", "lab_results", ["doctor_id"])

    op.create_table(
        "lab_result_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lab_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lab_order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_code", sa.Text(), nullable=False),
        sa.Column("test_name", sa.Text(), nullable=False),
        sa.Column("result_value", sa.Text(), nullable=False),
        sa.Column("result_unit", sa.Text(), nullable=True),
        sa.Column("reference_range", sa.Text(), nullable=True),
        sa.Column("abnormal_flag", abnormal_flag_enum, nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=True),
        *_audit_columns_no_soft_delete(),
        sa.PrimaryKeyConstraint("id", name="pk_lab_result_items"),
        sa.ForeignKeyConstraint(
            ["lab_result_id"],
            ["lab_results.id"],
            name="fk_lab_result_items_lab_result_id_lab_results",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lab_order_item_id"],
            ["lab_order_items.id"],
            name="fk_lab_result_items_lab_order_item_id_lab_order_items",
            ondelete="RESTRICT",
        ),
        *_audit_fks("lab_result_items"),
    )
    op.create_index("ix_lab_result_items_lab_result_id", "lab_result_items", ["lab_result_id"])
    op.create_index(
        "ix_lab_result_items_lab_order_item_id", "lab_result_items", ["lab_order_item_id"]
    )


def downgrade() -> None:
    op.drop_table("lab_result_items")
    op.drop_table("lab_results")

    postgresql.ENUM(name="abnormal_flag_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="lab_result_status_enum").drop(op.get_bind(), checkfirst=True)
