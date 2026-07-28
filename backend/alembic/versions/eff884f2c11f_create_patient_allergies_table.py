"""create patient allergies table

Creates the Patient Allergies foundation schema: patient_allergies
(many-to-one with `patients`, the Patient module's own table).

`organization_id` references `organizations.id`, `patient_id` references
`patients.id`, and `verified_by` references `doctors.id` (the Doctor
module's table, chained before this migration) — this is why this
migration's `down_revision` chains after the Patient Contacts migration,
not a modification to any prior module's tables. No column is added to,
or constraint changed on, `organizations`/`patients`/`doctors`/`users`/
any other prior table here.

`verified_by` uses `ON DELETE SET NULL` rather than `RESTRICT` — see
`PatientAllergyModel.verified_by`'s own comment for why (mirrors
`AuditActorMixin`'s `created_by`/`updated_by` reasoning: historical
attribution is best-effort, not load-bearing, so it must not block a
doctor row from ever being removed).

The "duplicate active allergy (same patient + allergen) is not allowed"
business rule is enforced by a partial unique index on
`(patient_id, allergen_name) WHERE status = 'active' AND deleted_at IS
NULL`; `allergen_name` is `CITEXT` so that index (and the application
layer's own pre-check) treats allergen names case-insensitively — the
same reasoning `email` columns use `CITEXT` everywhere else in this
schema, applied here because two differently-cased entries for what is
clinically the same allergen would otherwise defeat the point of the
uniqueness rule. The "verified_date cannot exist without verified_by"
pairing rule is enforced at both layers: `PatientAllergy.__post_init__`
(so an invalid state can never exist in memory) and a DB `CHECK`
constraint here (defense-in-depth against writes that bypass the domain
layer entirely, e.g. a direct SQL edit) — unlike `DoctorSchedule`'s
`break_start`/`break_end` pairing rule, which is domain-layer only.

Revision ID: eff884f2c11f
Revises: d4b5f3913c60
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "eff884f2c11f"
down_revision: str | None = "d4b5f3913c60"
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
    allergy_type_enum = postgresql.ENUM(
        "drug",
        "food",
        "environmental",
        "insect",
        "latex",
        "other",
        name="allergy_type_enum",
        create_type=False,
    )
    allergy_type_enum.create(op.get_bind(), checkfirst=True)

    allergy_severity_enum = postgresql.ENUM(
        "mild",
        "moderate",
        "severe",
        "life_threatening",
        name="allergy_severity_enum",
        create_type=False,
    )
    allergy_severity_enum.create(op.get_bind(), checkfirst=True)

    allergy_status_enum = postgresql.ENUM(
        "active",
        "resolved",
        name="allergy_status_enum",
        create_type=False,
    )
    allergy_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "patient_allergies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allergy_type", allergy_type_enum, nullable=False),
        sa.Column("allergen_name", postgresql.CITEXT(), nullable=False),
        sa.Column("severity", allergy_severity_enum, nullable=False),
        sa.Column("reaction", sa.Text(), nullable=True),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("status", allergy_status_enum, nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_date", sa.Date(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_patient_allergies"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_patient_allergies_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_patient_allergies_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["doctors.id"],
            name="fk_patient_allergies_verified_by_doctors",
            ondelete="SET NULL",
        ),
        *_audit_fks("patient_allergies"),
        sa.CheckConstraint(
            "verified_date IS NULL OR verified_by IS NOT NULL",
            name="verified_date_requires_verified_by",
        ),
    )
    op.create_index(
        "uq_patient_allergies_active_per_patient_and_allergen",
        "patient_allergies",
        ["patient_id", "allergen_name"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND deleted_at IS NULL"),
    )
    op.create_index("ix_patient_allergies_patient_id", "patient_allergies", ["patient_id"])


def downgrade() -> None:
    op.drop_table("patient_allergies")

    postgresql.ENUM(name="allergy_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="allergy_severity_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="allergy_type_enum").drop(op.get_bind(), checkfirst=True)
