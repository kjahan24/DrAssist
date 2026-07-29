"""create prescriptions tables

Creates the Prescription foundation schema: prescriptions and
prescription_items.

`prescriptions.organization_id` references `organizations.id`,
`clinical_note_id` references `clinical_notes.id`, `patient_id`
references `patients.id`, `visit_id` references `patient_visits.id`, and
`doctor_id` references `doctors.id` (all chained before this migration) —
this is why this migration's `down_revision` chains after the SOAP Notes
migration, not a modification to any prior module's tables. No column is
added to, or constraint changed on, `organizations`/`clinical_notes`/
`patients`/`patient_visits`/`doctors`/`soap_notes`/`users`/any other
prior table here.

`clinical_note_id`, `patient_id`, and `visit_id` all use `ON DELETE
CASCADE`, matching `soap_notes`' own choice for the identical three
columns: a prescription has no independent lifecycle meaning without its
clinical note, and `patient_id`/`visit_id` are derived copies of
`clinical_notes`' own columns. `doctor_id` (required) uses `ON DELETE
RESTRICT`, also matching `soap_notes.doctor_id`.

"One Clinical Note can have at most one Prescription" is enforced by a
partial unique index on `clinical_note_id WHERE deleted_at IS NULL`, the
same one-to-one shape `soap_notes.clinical_note_id` already uses.
"prescription_number is globally unique" is enforced by a partial unique
index on `prescription_number WHERE deleted_at IS NULL`, the same shape
`clinical_notes.note_number` already uses.

`prescription_items.prescription_id` uses `ON DELETE CASCADE`:
"Prescription Items cannot exist without a Prescription" is a hard
existence dependency, so a deleted prescription's items must not survive
as orphans. `prescription_items` carries no `organization_id` column and
no `deleted_at` column — this task's own field list for `PrescriptionItem`
lists neither (tenant scoping is inherited transitively via
`prescription_id -> prescriptions.organization_id`, and only
"timestamps"/"audit fields" are listed, not "soft delete") — see
`PrescriptionItemModel`'s own comment for the full reasoning.

Unlike `clinical_notes`, there is **no** `CHECK` constraint here enforcing
"a Final Prescription must contain at least one Prescription Item": a
`CHECK` constraint can only see this table's own row, never count rows in
a different table — that invariant is enforced exclusively at the
application layer (`application/use_cases/finalize_prescription.py`).

Revision ID: d7b7f088c9c3
Revises: f9cec12d02f1
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7b7f088c9c3"
down_revision: str | None = "f9cec12d02f1"
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
    """`prescription_items` omits `deleted_at` — see this migration's own
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
    prescription_status_enum = postgresql.ENUM(
        "draft",
        "final",
        name="prescription_status_enum",
        create_type=False,
    )
    prescription_status_enum.create(op.get_bind(), checkfirst=True)

    administration_route_enum = postgresql.ENUM(
        "oral",
        "iv",
        "im",
        "sc",
        "topical",
        "inhalation",
        "ophthalmic",
        "otic",
        "nasal",
        "rectal",
        "vaginal",
        "other",
        name="administration_route_enum",
        create_type=False,
    )
    administration_route_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "prescriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_number", sa.Text(), nullable=False),
        sa.Column("prescription_date", sa.Date(), nullable=False),
        sa.Column("status", prescription_status_enum, nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_prescriptions"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_prescriptions_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinical_note_id"],
            ["clinical_notes.id"],
            name="fk_prescriptions_clinical_note_id_clinical_notes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_prescriptions_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_prescriptions_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_prescriptions_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        *_audit_fks("prescriptions"),
    )
    op.create_index(
        "uq_prescriptions_clinical_note_id",
        "prescriptions",
        ["clinical_note_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_prescriptions_prescription_number",
        "prescriptions",
        ["prescription_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_prescriptions_organization_id", "prescriptions", ["organization_id"])
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"])
    op.create_index("ix_prescriptions_visit_id", "prescriptions", ["visit_id"])
    op.create_index("ix_prescriptions_doctor_id", "prescriptions", ["doctor_id"])

    op.create_table(
        "prescription_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medication_name", sa.Text(), nullable=False),
        sa.Column("generic_name", sa.Text(), nullable=True),
        sa.Column("strength", sa.Text(), nullable=False),
        sa.Column("dosage", sa.Text(), nullable=False),
        sa.Column("dosage_unit", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=False),
        sa.Column("route", administration_route_enum, nullable=False),
        sa.Column("duration", sa.Text(), nullable=False),
        sa.Column("duration_unit", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        *_audit_columns_no_soft_delete(),
        sa.PrimaryKeyConstraint("id", name="pk_prescription_items"),
        sa.ForeignKeyConstraint(
            ["prescription_id"],
            ["prescriptions.id"],
            name="fk_prescription_items_prescription_id_prescriptions",
            ondelete="CASCADE",
        ),
        *_audit_fks("prescription_items"),
    )
    op.create_index(
        "ix_prescription_items_prescription_id", "prescription_items", ["prescription_id"]
    )


def downgrade() -> None:
    op.drop_table("prescription_items")
    op.drop_table("prescriptions")

    postgresql.ENUM(name="administration_route_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="prescription_status_enum").drop(op.get_bind(), checkfirst=True)
