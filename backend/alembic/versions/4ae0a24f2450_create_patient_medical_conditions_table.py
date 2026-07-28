"""create patient medical conditions table

Creates the Patient Medical Conditions foundation schema:
patient_medical_conditions (many-to-one with `patients`, the Patient
module's own table).

`organization_id` references `organizations.id`, `patient_id` references
`patients.id`, and `diagnosed_by` references `doctors.id` (the Doctor
module's table, chained before this migration) — this is why this
migration's `down_revision` chains after the Patient Medications
migration, not a modification to any prior module's tables. No column is
added to, or constraint changed on, `organizations`/`patients`/`doctors`/
`users`/any other prior table here.

`diagnosed_by` uses `ON DELETE SET NULL` rather than `RESTRICT` — the
same reasoning as `patient_allergies.verified_by`/
`patient_medications.prescribed_by`: historical attribution is
best-effort, not load-bearing, so it must not block a doctor row from
ever being removed.

"Duplicate active conditions are not allowed" is enforced by a partial
unique index on `(patient_id, condition_name) WHERE status = 'active' AND
deleted_at IS NULL`; `condition_name` is `CITEXT` for the same
case-insensitive-duplicate reasoning `patient_allergies.allergen_name`
already documents. Two more business rules are enforced as DB `CHECK`
constraints (in addition to `PatientMedicalCondition.__post_init__`, the
same defense-in-depth pattern applied to Patient Allergies/Medications):
- "resolved_date must be after diagnosis_date" ->
  `resolved_date IS NULL OR resolved_date > diagnosis_date` (strict
  "after", unlike Patient Medications' "not before" which allows the
  same day).
- "chronic conditions cannot have status 'Resolved' unless resolved_date
  exists" -> `NOT is_chronic OR status != 'resolved' OR resolved_date IS
  NOT NULL` (violated only when is_chronic is true, status is
  'resolved', and resolved_date is null).

Revision ID: 4ae0a24f2450
Revises: b259793bb6ab
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4ae0a24f2450"
down_revision: str | None = "b259793bb6ab"
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
    condition_severity_enum = postgresql.ENUM(
        "mild",
        "moderate",
        "severe",
        name="condition_severity_enum",
        create_type=False,
    )
    condition_severity_enum.create(op.get_bind(), checkfirst=True)

    condition_status_enum = postgresql.ENUM(
        "active",
        "resolved",
        "chronic",
        "in_remission",
        name="condition_status_enum",
        create_type=False,
    )
    condition_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "patient_medical_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diagnosed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("condition_name", postgresql.CITEXT(), nullable=False),
        sa.Column("icd10_code", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("severity", condition_severity_enum, nullable=False),
        sa.Column("diagnosis_date", sa.Date(), nullable=False),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("status", condition_status_enum, nullable=False, server_default="active"),
        sa.Column("is_chronic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_infectious", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_date", sa.Date(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_patient_medical_conditions"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_patient_medical_conditions_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_patient_medical_conditions_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["diagnosed_by"],
            ["doctors.id"],
            name="fk_patient_medical_conditions_diagnosed_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("patient_medical_conditions"),
        sa.CheckConstraint(
            "resolved_date IS NULL OR resolved_date > diagnosis_date",
            name="resolved_after_diagnosis",
        ),
        sa.CheckConstraint(
            "NOT is_chronic OR status != 'resolved' OR resolved_date IS NOT NULL",
            name="chronic_resolved_requires_date",
        ),
    )
    op.create_index(
        "uq_patient_medical_conditions_active_per_patient_and_name",
        "patient_medical_conditions",
        ["patient_id", "condition_name"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_patient_medical_conditions_patient_id", "patient_medical_conditions", ["patient_id"]
    )


def downgrade() -> None:
    op.drop_table("patient_medical_conditions")

    postgresql.ENUM(name="condition_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="condition_severity_enum").drop(op.get_bind(), checkfirst=True)
