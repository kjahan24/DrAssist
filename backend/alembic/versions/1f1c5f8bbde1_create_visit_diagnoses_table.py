"""create visit diagnoses table

Creates the Diagnosis foundation schema: visit_diagnoses.

`organization_id` references `organizations.id` and `visit_id` references
`patient_visits.id` (both chained before this migration) — this is why
this migration's `down_revision` chains after the Chief Complaints
migration, not a modification to any prior module's tables. No column is
added to, or constraint changed on, `organizations`/`patient_visits`/
`doctors`/`users`/any other prior table here.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_chief_complaints.visit_id` already makes: a diagnosis has no
independent lifecycle meaning without its visit. `diagnosed_by`
(nullable, best-effort attribution) uses `ON DELETE SET NULL`, matching
`visit_chief_complaints.recorded_by`.

Two uniqueness rules, both partial indexes scoped `WHERE deleted_at IS
NULL`:
- "sequence_number must be unique within a Visit" -> unique on
  `(visit_id, sequence_number)`, the same shape
  `visit_chief_complaints`' own sequence uniqueness already uses.
- "Only one Primary diagnosis is allowed per Visit" -> unique on
  `visit_id` additionally scoped `WHERE diagnosis_type = 'primary'` — the
  same *shape* `doctor_specializations`' "one primary per doctor" index
  uses, guaranteeing the invariant at the database level even though the
  application layer enforces it via rejection rather than auto-unset
  (see `VisitDiagnosisModel`'s own comment for why).

One further business rule is enforced as a DB `CHECK` constraint (in
addition to `VisitDiagnosis.__post_init__`, the same defense-in-depth
pattern applied to every prior module):
- "A Ruled Out diagnosis cannot be marked as Primary" ->
  `NOT (diagnosis_type = 'primary' AND diagnosis_status = 'ruled_out')`.
- "sequence_number starts from 1" -> `sequence_number >= 1`.

Revision ID: 1f1c5f8bbde1
Revises: e1751c39a671
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1f1c5f8bbde1"
down_revision: str | None = "e1751c39a671"
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
    diagnosis_type_enum = postgresql.ENUM(
        "primary",
        "secondary",
        "differential",
        name="diagnosis_type_enum",
        create_type=False,
    )
    diagnosis_type_enum.create(op.get_bind(), checkfirst=True)

    diagnosis_status_enum = postgresql.ENUM(
        "provisional",
        "confirmed",
        "ruled_out",
        name="diagnosis_status_enum",
        create_type=False,
    )
    diagnosis_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "visit_diagnoses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.SmallInteger(), nullable=False),
        sa.Column("diagnosis_name", sa.Text(), nullable=False),
        sa.Column("icd10_code", sa.Text(), nullable=True),
        sa.Column("diagnosis_type", diagnosis_type_enum, nullable=False),
        sa.Column(
            "diagnosis_status", diagnosis_status_enum, nullable=False, server_default="provisional"
        ),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("diagnosed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diagnosed_at", _TIMESTAMPTZ, nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_visit_diagnoses"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_visit_diagnoses_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_visit_diagnoses_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["diagnosed_by"],
            ["doctors.id"],
            name="fk_visit_diagnoses_diagnosed_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("visit_diagnoses"),
        sa.CheckConstraint("sequence_number >= 1", name="sequence_number_starts_at_one"),
        sa.CheckConstraint(
            "NOT (diagnosis_type = 'primary' AND diagnosis_status = 'ruled_out')",
            name="primary_not_ruled_out",
        ),
    )
    op.create_index(
        "uq_visit_diagnoses_visit_id_sequence_number",
        "visit_diagnoses",
        ["visit_id", "sequence_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_visit_diagnoses_primary_per_visit",
        "visit_diagnoses",
        ["visit_id"],
        unique=True,
        postgresql_where=sa.text("diagnosis_type = 'primary' AND deleted_at IS NULL"),
    )
    op.create_index("ix_visit_diagnoses_organization_id", "visit_diagnoses", ["organization_id"])


def downgrade() -> None:
    op.drop_table("visit_diagnoses")

    postgresql.ENUM(name="diagnosis_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="diagnosis_type_enum").drop(op.get_bind(), checkfirst=True)
