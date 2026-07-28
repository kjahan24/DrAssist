"""create patient medications table

Creates the Patient Medications foundation schema: patient_medications
(many-to-one with `patients`, the Patient module's own table).

`organization_id` references `organizations.id`, `patient_id` references
`patients.id`, and `prescribed_by` references `doctors.id` (the Doctor
module's table, chained before this migration) — this is why this
migration's `down_revision` chains after the Patient Allergies
migration, not a modification to any prior module's tables. No column is
added to, or constraint changed on, `organizations`/`patients`/`doctors`/
`users`/any other prior table here.

`prescribed_by` uses `ON DELETE SET NULL` rather than `RESTRICT` — the
same reasoning as `patient_allergies.verified_by` (see that migration's
own docstring): historical attribution is best-effort, not load-bearing,
so it must not block a doctor row from ever being removed.

Unlike Patient Allergies, there is no duplicate-prevention rule here — "a
patient may have multiple medications" is explicit — so no unique index
is created beyond the primary key.

Two business rules are enforced as DB `CHECK` constraints (in addition to
`PatientMedication.__post_init__`, the same defense-in-depth reasoning
applied to Patient Allergies' `verified_date`/`verified_by` pairing):
- "current medications cannot have an end_date before start_date" ->
  `end_date IS NULL OR end_date >= start_date` (note: "before", not
  "before or on", so same-day start/end is allowed).
- "if is_current = false and treatment is completed, end_date is
  required" -> `is_current OR adherence_status != 'completed' OR
  end_date IS NOT NULL` (violated only when is_current is false,
  adherence_status is 'completed', and end_date is null).

Revision ID: b259793bb6ab
Revises: eff884f2c11f
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b259793bb6ab"
down_revision: str | None = "eff884f2c11f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def _audit_columns() -> list[sa.Column]:
    """The five standard columns every table in this schema carries, minus
    `id` (added separately since its type/default is identical everywhere
    but declared first). See `docs/database/00_overview.md`.
    """
    return [
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("deleted_at", _TIMESTAMPTZ, nullable=True),
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
    route_of_administration_enum = postgresql.ENUM(
        "oral",
        "iv",
        "im",
        "sc",
        "topical",
        "inhalation",
        "other",
        name="route_of_administration_enum",
        create_type=False,
    )
    route_of_administration_enum.create(op.get_bind(), checkfirst=True)

    adherence_status_enum = postgresql.ENUM(
        "taking",
        "stopped",
        "completed",
        "unknown",
        name="adherence_status_enum",
        create_type=False,
    )
    adherence_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "patient_medications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prescribed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("medication_name", sa.Text(), nullable=False),
        sa.Column("generic_name", sa.Text(), nullable=True),
        sa.Column("brand_name", sa.Text(), nullable=True),
        sa.Column("dosage", sa.Text(), nullable=False),
        sa.Column("dosage_unit", sa.Text(), nullable=True),
        sa.Column("route", route_of_administration_enum, nullable=False),
        sa.Column("frequency", sa.Text(), nullable=True),
        sa.Column("indication", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "adherence_status", adherence_status_enum, nullable=False, server_default="taking"
        ),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_patient_medications"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_patient_medications_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_patient_medications_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prescribed_by"],
            ["doctors.id"],
            name="fk_patient_medications_prescribed_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("patient_medications"),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="end_date_not_before_start_date"
        ),
        sa.CheckConstraint(
            "is_current OR adherence_status != 'completed' OR end_date IS NOT NULL",
            name="end_date_required_for_completed",
        ),
    )
    op.create_index("ix_patient_medications_patient_id", "patient_medications", ["patient_id"])


def downgrade() -> None:
    op.drop_table("patient_medications")

    postgresql.ENUM(name="adherence_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="route_of_administration_enum").drop(op.get_bind(), checkfirst=True)
