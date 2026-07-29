"""create visit procedures table

Creates the Procedures foundation schema: visit_procedures.

`organization_id` references `organizations.id` and `visit_id` references
`patient_visits.id` (both chained before this migration) — this is why
this migration's `down_revision` chains after the Diagnosis migration,
not a modification to any prior module's tables. No column is added to,
or constraint changed on, `organizations`/`patient_visits`/`doctors`/
`users`/any other prior table here.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_diagnoses.visit_id` already makes: a procedure has no independent
lifecycle meaning without its visit. `performed_by` (nullable,
best-effort attribution) uses `ON DELETE SET NULL`, matching
`visit_diagnoses.diagnosed_by`.

"sequence_number must be unique within a Visit" is enforced by a partial
unique index on `(visit_id, sequence_number) WHERE deleted_at IS NULL`,
the same shape `visit_diagnoses`' own sequence uniqueness already uses.

Three business rules are enforced as DB `CHECK` constraints (in addition
to `VisitProcedure.__post_init__`, the same defense-in-depth pattern
applied to every prior module):
- "sequence_number starts from 1" -> `sequence_number >= 1`.
- "performed_at is required only when status = Completed" ->
  `procedure_status != 'completed' OR performed_at IS NOT NULL`.
- "Cancelled procedures cannot have performed_at" ->
  `procedure_status != 'cancelled' OR performed_at IS NULL`.

Revision ID: cf2ff02702b8
Revises: 1f1c5f8bbde1
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "cf2ff02702b8"
down_revision: str | None = "1f1c5f8bbde1"
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
    procedure_status_enum = postgresql.ENUM(
        "planned",
        "in_progress",
        "completed",
        "cancelled",
        name="procedure_status_enum",
        create_type=False,
    )
    procedure_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "visit_procedures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.SmallInteger(), nullable=False),
        sa.Column("procedure_name", sa.Text(), nullable=False),
        sa.Column("procedure_code", sa.Text(), nullable=True),
        sa.Column("procedure_category", sa.Text(), nullable=True),
        sa.Column(
            "procedure_status", procedure_status_enum, nullable=False, server_default="planned"
        ),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("performed_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_visit_procedures"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_visit_procedures_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_visit_procedures_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"],
            ["doctors.id"],
            name="fk_visit_procedures_performed_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("visit_procedures"),
        sa.CheckConstraint("sequence_number >= 1", name="sequence_number_starts_at_one"),
        sa.CheckConstraint(
            "procedure_status != 'completed' OR performed_at IS NOT NULL",
            name="completed_requires_performed_at",
        ),
        sa.CheckConstraint(
            "procedure_status != 'cancelled' OR performed_at IS NULL",
            name="cancelled_forbids_performed_at",
        ),
    )
    op.create_index(
        "uq_visit_procedures_visit_id_sequence_number",
        "visit_procedures",
        ["visit_id", "sequence_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_visit_procedures_organization_id", "visit_procedures", ["organization_id"])


def downgrade() -> None:
    op.drop_table("visit_procedures")

    postgresql.ENUM(name="procedure_status_enum").drop(op.get_bind(), checkfirst=True)
