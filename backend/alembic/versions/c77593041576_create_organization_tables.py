"""create organization tables

Creates the Organization module's foundation schema: organizations,
organization_settings (one-to-one with organizations), departments
(many-to-one with organizations).

`created_by`/`updated_by` on all three tables reference `users.id` (the
Authentication module's table), via the same shared `AuditActorMixin`
every table in this schema uses — this is why this migration's
`down_revision` chains after the Authentication migration, not a
modification to Authentication's own tables. No column is added to, or
constraint changed on, `users`/`roles`/`permissions`/`role_permissions`/
`user_roles`/`user_sessions`/`refresh_tokens` here; the deferred
`organization_id` foreign key on those tables (noted in the Authentication
migration's docstring) remains deferred, per this task's explicit scope.

Revision ID: c77593041576
Revises: dd4c7542b13e
Create Date: 2026-07-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c77593041576"
down_revision: str | None = "dd4c7542b13e"
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
    organization_type_enum = postgresql.ENUM(
        "clinic", "hospital", "diagnostic", "telemedicine",
        name="organization_type_enum",
        create_type=False,
    )
    organization_type_enum.create(op.get_bind(), checkfirst=True)

    department_status_enum = postgresql.ENUM(
        "active", "inactive",
        name="department_status_enum",
        create_type=False,
    )
    department_status_enum.create(op.get_bind(), checkfirst=True)

    # --- organizations ---------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=True),
        sa.Column("type", organization_type_enum, nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("tax_number", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        *_audit_fks("organizations"),
    )
    op.create_index(
        "uq_organizations_organization_code",
        "organizations",
        ["organization_code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_organizations_is_active", "organizations", ["is_active"])

    # --- organization_settings --------------------------------------------
    op.create_table(
        "organization_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "working_hours", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "appointment_duration_minutes", sa.SmallInteger(), nullable=False, server_default="30"
        ),
        sa.Column("default_timezone", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("default_language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("default_currency", sa.Text(), nullable=False, server_default="USD"),
        sa.Column(
            "feature_flags", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "ai_settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "notification_settings",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_organization_settings"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_settings_organization_id_organizations",
            ondelete="CASCADE",
        ),
        *_audit_fks("organization_settings"),
        sa.CheckConstraint(
            "appointment_duration_minutes > 0", name="appointment_duration_minutes_positive"
        ),
    )
    op.create_index(
        "uq_organization_settings_organization_id",
        "organization_settings",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # --- departments -------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", department_status_enum, nullable=False, server_default="active"),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_departments_organization_id_organizations",
            ondelete="CASCADE",
        ),
        *_audit_fks("departments"),
    )
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])


def downgrade() -> None:
    op.drop_table("departments")
    op.drop_table("organization_settings")
    op.drop_table("organizations")

    postgresql.ENUM(name="department_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="organization_type_enum").drop(op.get_bind(), checkfirst=True)
