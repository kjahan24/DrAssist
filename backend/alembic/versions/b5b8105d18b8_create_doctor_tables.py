"""create doctor tables

Creates the Doctor module's foundation schema: doctors, doctor_profiles
(one-to-one with doctors), doctor_licenses, doctor_specializations,
doctor_schedules (many-to-one with doctors).

`doctors.organization_id`/`doctor_specializations.organization_id`
reference `organizations.id` (the Organization module's table) and
`doctors.user_id` references `users.id` (the Authentication module's
table) — this is why this migration's `down_revision` chains after the
Organization migration, not a modification to either prior module's
tables. No column is added to, or constraint changed on,
`organizations`/`organization_settings`/`departments`/`users`/`roles`/
`permissions`/`role_permissions`/`user_roles`/`user_sessions`/
`refresh_tokens` here.

Revision ID: b5b8105d18b8
Revises: c77593041576
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b5b8105d18b8"
down_revision: str | None = "c77593041576"
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
    doctor_status_enum = postgresql.ENUM(
        "active",
        "inactive",
        "suspended",
        name="doctor_status_enum",
        create_type=False,
    )
    doctor_status_enum.create(op.get_bind(), checkfirst=True)

    gender_enum = postgresql.ENUM(
        "male",
        "female",
        "other",
        name="gender_enum",
        create_type=False,
    )
    gender_enum.create(op.get_bind(), checkfirst=True)

    license_verification_status_enum = postgresql.ENUM(
        "pending",
        "verified",
        "rejected",
        name="license_verification_status_enum",
        create_type=False,
    )
    license_verification_status_enum.create(op.get_bind(), checkfirst=True)

    day_of_week_enum = postgresql.ENUM(
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        name="day_of_week_enum",
        create_type=False,
    )
    day_of_week_enum.create(op.get_bind(), checkfirst=True)

    # --- doctors -----------------------------------------------------------
    op.create_table(
        "doctors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", sa.Text(), nullable=False),
        sa.Column("status", doctor_status_enum, nullable=False, server_default="active"),
        sa.Column("joining_date", sa.Date(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctors"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_doctors_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_doctors_user_id_users", ondelete="RESTRICT"
        ),
        *_audit_fks("doctors"),
    )
    op.create_index(
        "uq_doctors_organization_id_employee_id",
        "doctors",
        ["organization_id", "employee_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_doctors_user_id",
        "doctors",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_doctors_organization_id", "doctors", ["organization_id"])

    # --- doctor_profiles -----------------------------------------------------
    op.create_table(
        "doctor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("gender", gender_enum, nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("years_of_experience", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("qualification", sa.Text(), nullable=True),
        sa.Column("consultation_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("profile_photo_url", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_profiles"),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_profiles_doctor_id_doctors",
            ondelete="CASCADE",
        ),
        *_audit_fks("doctor_profiles"),
        sa.CheckConstraint(
            "years_of_experience >= 0", name="ck_doctor_profiles_years_of_experience_nonneg"
        ),
    )
    op.create_index(
        "uq_doctor_profiles_doctor_id",
        "doctor_profiles",
        ["doctor_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # --- doctor_licenses -----------------------------------------------------
    op.create_table(
        "doctor_licenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("license_number", sa.Text(), nullable=False),
        sa.Column("issuing_authority", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column(
            "verification_status",
            license_verification_status_enum,
            nullable=False,
            server_default="pending",
        ),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_licenses"),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_licenses_doctor_id_doctors",
            ondelete="CASCADE",
        ),
        *_audit_fks("doctor_licenses"),
        sa.CheckConstraint(
            "expiry_date > issue_date", name="ck_doctor_licenses_expiry_after_issue"
        ),
    )
    op.create_index(
        "uq_doctor_licenses_license_number",
        "doctor_licenses",
        ["license_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_doctor_licenses_doctor_id", "doctor_licenses", ["doctor_id"])

    # --- doctor_specializations ----------------------------------------------
    op.create_table(
        "doctor_specializations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialization_name", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("years_of_experience", sa.SmallInteger(), nullable=False, server_default="0"),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_specializations"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_doctor_specializations_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_specializations_doctor_id_doctors",
            ondelete="CASCADE",
        ),
        *_audit_fks("doctor_specializations"),
        sa.CheckConstraint(
            "years_of_experience >= 0",
            name="ck_doctor_specializations_specialization_years_nonneg",
        ),
    )
    op.create_index(
        "uq_doctor_specializations_primary_per_doctor",
        "doctor_specializations",
        ["doctor_id"],
        unique=True,
        postgresql_where=sa.text("is_primary AND deleted_at IS NULL"),
    )
    op.create_index("ix_doctor_specializations_doctor_id", "doctor_specializations", ["doctor_id"])

    # --- doctor_schedules ------------------------------------------------------
    op.create_table(
        "doctor_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", day_of_week_enum, nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_schedules"),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_schedules_doctor_id_doctors",
            ondelete="CASCADE",
        ),
        *_audit_fks("doctor_schedules"),
        sa.CheckConstraint("start_time < end_time", name="ck_doctor_schedules_start_before_end"),
    )
    op.create_index(
        "ix_doctor_schedules_doctor_id_day_of_week",
        "doctor_schedules",
        ["doctor_id", "day_of_week"],
    )


def downgrade() -> None:
    op.drop_table("doctor_schedules")
    op.drop_table("doctor_specializations")
    op.drop_table("doctor_licenses")
    op.drop_table("doctor_profiles")
    op.drop_table("doctors")

    postgresql.ENUM(name="day_of_week_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="license_verification_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="gender_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="doctor_status_enum").drop(op.get_bind(), checkfirst=True)
