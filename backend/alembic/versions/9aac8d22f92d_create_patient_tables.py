"""create patient tables

Creates the Patient module's foundation schema: patients.

`patients.organization_id` references `organizations.id` (the
Organization module's table) — this is why this migration's
`down_revision` chains after the Doctor migration, not a modification to
any prior module's tables. No column is added to, or constraint changed
on, `organizations`/`organization_settings`/`departments`/`users`/`roles`/
`permissions`/`role_permissions`/`user_roles`/`user_sessions`/
`refresh_tokens`/`doctors`/`doctor_profiles`/`doctor_licenses`/
`doctor_specializations`/`doctor_schedules` here.

The four new enum types (`patient_status_enum`, `patient_gender_enum`,
`blood_group_enum`, `marital_status_enum`) are deliberately named apart
from the Doctor module's own `doctor_status_enum`/`gender_enum` — even
though `patient_gender_enum` shares Doctor's `Gender` values, reusing
Doctor's Postgres type would couple this migration to Doctor's, which
violates module independence (see
`app.modules.patient.domain.enums.Gender`'s docstring for the same
reasoning at the domain layer).

Revision ID: 9aac8d22f92d
Revises: b5b8105d18b8
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9aac8d22f92d"
down_revision: str | None = "b5b8105d18b8"
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
    patient_status_enum = postgresql.ENUM(
        "active",
        "inactive",
        "deceased",
        name="patient_status_enum",
        create_type=False,
    )
    patient_status_enum.create(op.get_bind(), checkfirst=True)

    patient_gender_enum = postgresql.ENUM(
        "male",
        "female",
        "other",
        name="patient_gender_enum",
        create_type=False,
    )
    patient_gender_enum.create(op.get_bind(), checkfirst=True)

    blood_group_enum = postgresql.ENUM(
        "a+",
        "a-",
        "b+",
        "b-",
        "ab+",
        "ab-",
        "o+",
        "o-",
        name="blood_group_enum",
        create_type=False,
    )
    blood_group_enum.create(op.get_bind(), checkfirst=True)

    marital_status_enum = postgresql.ENUM(
        "single",
        "married",
        "divorced",
        "widowed",
        "separated",
        name="marital_status_enum",
        create_type=False,
    )
    marital_status_enum.create(op.get_bind(), checkfirst=True)

    # --- patients ------------------------------------------------------------
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_number", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("middle_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("preferred_name", sa.Text(), nullable=True),
        sa.Column("gender", patient_gender_enum, nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("blood_group", blood_group_enum, nullable=True),
        sa.Column("marital_status", marital_status_enum, nullable=True),
        sa.Column("national_id", sa.Text(), nullable=True),
        sa.Column("passport_number", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("occupation", sa.Text(), nullable=True),
        sa.Column("nationality", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("religion", sa.Text(), nullable=True),
        sa.Column("address_line_1", sa.Text(), nullable=True),
        sa.Column("address_line_2", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("status", patient_status_enum, nullable=False, server_default="active"),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_patients_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        *_audit_fks("patients"),
    )
    op.create_index(
        "uq_patients_organization_id_patient_number",
        "patients",
        ["organization_id", "patient_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_patients_organization_id", "patients", ["organization_id"])


def downgrade() -> None:
    op.drop_table("patients")

    postgresql.ENUM(name="marital_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="blood_group_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="patient_gender_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="patient_status_enum").drop(op.get_bind(), checkfirst=True)
