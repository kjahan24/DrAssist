"""create visit chief complaints table

Creates the Chief Complaints foundation schema: visit_chief_complaints.

`organization_id` references `organizations.id` and `visit_id` references
`patient_visits.id` (both chained before this migration) — this is why
this migration's `down_revision` chains after the Vital Signs migration,
not a modification to any prior module's tables. No column is added to,
or constraint changed on, `organizations`/`patient_visits`/`doctors`/
`users`/any other prior table here.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_vital_signs.visit_id` already makes: a chief complaint has no
independent lifecycle meaning without its visit. `recorded_by` (nullable,
best-effort attribution) uses `ON DELETE SET NULL`, matching
`visit_vital_signs.recorded_by`.

Unlike Vital Signs (one-to-one with a visit), a visit can have *many*
chief complaints, distinguished by `sequence_number` — "sequence_number
must be unique within a Visit" is enforced by a partial unique index on
`(visit_id, sequence_number) WHERE deleted_at IS NULL`, the same shape
`patient_visits`' own `(organization_id, visit_number)` uniqueness
already uses.

Three business rules are enforced as DB `CHECK` constraints (in addition
to `VisitChiefComplaint.__post_init__`, the same defense-in-depth pattern
applied to every prior module):
- "sequence_number starts from 1" -> `sequence_number >= 1`.
- "duration_value cannot be negative" -> `duration_value IS NULL OR
  duration_value >= 0`.
- "duration_unit is allowed only when duration_value exists" ->
  `duration_value IS NOT NULL OR duration_unit IS NULL`.

Revision ID: e1751c39a671
Revises: 594a15377bf6
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1751c39a671"
down_revision: str | None = "594a15377bf6"
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
    duration_unit_enum = postgresql.ENUM(
        "hours",
        "days",
        "weeks",
        "months",
        "years",
        name="duration_unit_enum",
        create_type=False,
    )
    duration_unit_enum.create(op.get_bind(), checkfirst=True)

    severity_enum = postgresql.ENUM(
        "mild",
        "moderate",
        "severe",
        name="severity_enum",
        create_type=False,
    )
    severity_enum.create(op.get_bind(), checkfirst=True)

    onset_enum = postgresql.ENUM(
        "sudden",
        "gradual",
        name="onset_enum",
        create_type=False,
    )
    onset_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "visit_chief_complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.SmallInteger(), nullable=False),
        sa.Column("complaint", sa.Text(), nullable=False),
        sa.Column("duration_value", sa.SmallInteger(), nullable=True),
        sa.Column("duration_unit", duration_unit_enum, nullable=True),
        sa.Column("severity", severity_enum, nullable=True),
        sa.Column("onset", onset_enum, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_at", _TIMESTAMPTZ, nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_visit_chief_complaints"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_visit_chief_complaints_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_visit_chief_complaints_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["doctors.id"],
            name="fk_visit_chief_complaints_recorded_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("visit_chief_complaints"),
        sa.CheckConstraint("sequence_number >= 1", name="sequence_number_starts_at_one"),
        sa.CheckConstraint(
            "duration_value IS NULL OR duration_value >= 0", name="duration_value_nonneg"
        ),
        sa.CheckConstraint(
            "duration_value IS NOT NULL OR duration_unit IS NULL",
            name="duration_unit_requires_value",
        ),
    )
    op.create_index(
        "uq_visit_chief_complaints_visit_id_sequence_number",
        "visit_chief_complaints",
        ["visit_id", "sequence_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_visit_chief_complaints_organization_id", "visit_chief_complaints", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_table("visit_chief_complaints")

    postgresql.ENUM(name="onset_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="severity_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="duration_unit_enum").drop(op.get_bind(), checkfirst=True)
