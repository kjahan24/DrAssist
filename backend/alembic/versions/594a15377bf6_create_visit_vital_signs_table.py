"""create visit vital signs table

Creates the Vital Signs foundation schema: visit_vital_signs.

`organization_id` references `organizations.id` and `visit_id` references
`patient_visits.id` (both chained before this migration) — this is why
this migration's `down_revision` chains after the Visit Core migration,
not a modification to any prior module's tables. No column is added to,
or constraint changed on, `organizations`/`patient_visits`/`doctors`/
`users`/any other prior table here.

`visit_id` uses `ON DELETE CASCADE`, not `RESTRICT`: a vital signs record
has no independent lifecycle meaning without its visit, the same
reasoning `doctor_profiles.doctor_id` already applies for the identical
one-to-one-with-CASCADE shape. `recorded_by` (nullable, best-effort
attribution) uses `ON DELETE SET NULL`, matching
`patient_allergies.verified_by`.

"One Visit has only one Vital Signs record" is enforced by a partial
unique index on `visit_id WHERE deleted_at IS NULL` — the same shape
`doctor_profiles.doctor_id`'s own one-to-one unique index already uses.

Six business rules are enforced as DB `CHECK` constraints (in addition to
`VisitVitalSigns.__post_init__`, the same defense-in-depth pattern
applied to every prior module):
- "Systolic BP must be greater than Diastolic BP" -> `systolic_bp >
  diastolic_bp`.
- "SpO2 must be between 0 and 100" -> `spo2 >= 0 AND spo2 <= 100`.
- "Temperature must be within a medically reasonable range" ->
  `temperature_c >= 25.0 AND temperature_c <= 45.0` (the extreme
  survivable range, not a "normal" clinical range — see
  `VisitVitalSignsModel`'s own comment).
- "Pulse ... must be positive" -> `pulse_bpm > 0`.
- "... and respiratory rate must be positive" -> `respiratory_rate > 0`.
- "Pain score must be between 0 and 10" -> `pain_score IS NULL OR
  (pain_score >= 0 AND pain_score <= 10)`.

`bmi` has no `CHECK` constraint: it is never set independently of
`height_cm`/`weight_kg` (always derived by the domain layer's
`calculate_bmi`), so there is no independent invariant for the database
to police.

Revision ID: 594a15377bf6
Revises: a21a9c63b7ce
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "594a15377bf6"
down_revision: str | None = "a21a9c63b7ce"
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
    op.create_table(
        "visit_vital_signs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("height_cm", sa.Numeric(5, 2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("bmi", sa.Numeric(4, 1), nullable=True),
        sa.Column("temperature_c", sa.Numeric(4, 1), nullable=False),
        sa.Column("pulse_bpm", sa.SmallInteger(), nullable=False),
        sa.Column("respiratory_rate", sa.SmallInteger(), nullable=False),
        sa.Column("systolic_bp", sa.SmallInteger(), nullable=False),
        sa.Column("diastolic_bp", sa.SmallInteger(), nullable=False),
        sa.Column("spo2", sa.SmallInteger(), nullable=False),
        sa.Column("blood_glucose", sa.Numeric(5, 1), nullable=True),
        sa.Column("pain_score", sa.SmallInteger(), nullable=True),
        sa.Column("recorded_at", _TIMESTAMPTZ, nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_visit_vital_signs"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_visit_vital_signs_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["patient_visits.id"],
            name="fk_visit_vital_signs_visit_id_patient_visits",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["doctors.id"],
            name="fk_visit_vital_signs_recorded_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("visit_vital_signs"),
        sa.CheckConstraint("systolic_bp > diastolic_bp", name="systolic_gt_diastolic"),
        sa.CheckConstraint("spo2 >= 0 AND spo2 <= 100", name="spo2_in_range"),
        sa.CheckConstraint(
            "temperature_c >= 25.0 AND temperature_c <= 45.0", name="temperature_in_range"
        ),
        sa.CheckConstraint("pulse_bpm > 0", name="pulse_positive"),
        sa.CheckConstraint("respiratory_rate > 0", name="respiratory_rate_positive"),
        sa.CheckConstraint(
            "pain_score IS NULL OR (pain_score >= 0 AND pain_score <= 10)",
            name="pain_score_in_range",
        ),
    )
    op.create_index(
        "uq_visit_vital_signs_visit_id",
        "visit_vital_signs",
        ["visit_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_visit_vital_signs_organization_id", "visit_vital_signs", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_table("visit_vital_signs")
