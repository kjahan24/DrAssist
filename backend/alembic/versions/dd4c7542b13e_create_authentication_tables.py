"""create authentication tables

Creates the Authentication module's foundation schema: users, roles,
permissions, role_permissions, user_roles, user_sessions, refresh_tokens.

Deliberately scoped to exactly the five entities this module's first
implementation task covers (User, Role, Permission, UserSession,
RefreshToken) — `auth_password_reset_tokens`, `auth_email_verification_tokens`,
and `auth_login_attempts` from the original schema design
(`docs/database/01_identity_and_access.md`) belong to the follow-up task
that adds the login/register flows which actually need them.

`organization_id` columns are present but **without** a foreign key to
`organizations` — the Organization module doesn't exist yet. The
constraint is deferred to a later migration once it does (the expand
pattern from `docs/database/08_migration_strategy.md §6`), not an
oversight.

Revision ID: dd4c7542b13e
Revises:
Create Date: 2026-07-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "dd4c7542b13e"
down_revision: str | None = None
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
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    user_status_enum = postgresql.ENUM(
        "invited", "active", "suspended", "deactivated",
        name="user_status_enum",
        create_type=False,
    )
    user_status_enum.create(op.get_bind(), checkfirst=True)

    # --- users -------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("status", user_status_enum, nullable=False, server_default="invited"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("email_verified_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("last_login_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("failed_login_attempts", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("locked_until", _TIMESTAMPTZ, nullable=True),
        sa.Column("timezone", sa.Text(), nullable=True),
        sa.Column("locale", sa.Text(), nullable=False, server_default="en-US"),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        *_audit_fks("users"),
        # `name=` is the bare constraint-name token: Base.metadata's "ck"
        # naming convention (`ck_%(table_name)s_%(constraint_name)s`) is
        # picked up by `op.create_table` via `target_metadata`
        # (`alembic/env.py`) and synthesizes the full
        # `ck_users_failed_login_attempts_nonneg` from it — passing the
        # already-fully-qualified name here doubles the prefix instead
        # (`ck_users_ck_users_...`), confirmed against a real Postgres
        # instance while building this migration.
        sa.CheckConstraint("failed_login_attempts >= 0", name="failed_login_attempts_nonneg"),
    )
    op.create_index(
        "uq_users_organization_id_email",
        "users",
        ["organization_id", "email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_status", "users", ["organization_id", "status"])

    # --- roles ---------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        *_audit_fks("roles"),
    )
    op.create_index(
        "uq_roles_system_name",
        "roles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "uq_roles_org_name",
        "roles",
        ["organization_id", "name"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_index("ix_roles_organization_id", "roles", ["organization_id"])

    # --- permissions -----------------------------------------------------
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        *_audit_fks("permissions"),
    )
    op.create_index(
        "uq_permissions_code",
        "permissions",
        ["code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])

    # --- role_permissions ------------------------------------------------
    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_role_permissions"),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_role_permissions_role_id_roles", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id_permissions",
            ondelete="CASCADE",
        ),
        *_audit_fks("role_permissions"),
    )
    op.create_index(
        "uq_role_permissions_role_permission",
        "role_permissions",
        ["role_id", "permission_id"],
        unique=True,
    )
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    # --- user_roles ------------------------------------------------------
    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("granted_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_user_roles"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_roles_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_user_roles_role_id_roles", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
            name="fk_user_roles_granted_by_users",
            ondelete="SET NULL",
        ),
        *_audit_fks("user_roles"),
    )
    op.create_index("uq_user_roles_user_role", "user_roles", ["user_id", "role_id"], unique=True)
    op.create_index("ix_user_roles_organization_id", "user_roles", ["organization_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # --- user_sessions ---------------------------------------------------
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_label", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("issued_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("expires_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("revoked_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.Column("last_used_at", _TIMESTAMPTZ, nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_sessions_user_id_users", ondelete="CASCADE"
        ),
        *_audit_fks("user_sessions"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_organization_id", "user_sessions", ["organization_id"])

    # --- refresh_tokens --------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("issued_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("expires_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("used_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("replaced_by_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(
            ["user_session_id"],
            ["user_sessions.id"],
            name="fk_refresh_tokens_user_session_id_user_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"],
            ["refresh_tokens.id"],
            name="fk_refresh_tokens_replaced_by_token_id_refresh_tokens",
            ondelete="SET NULL",
        ),
        *_audit_fks("refresh_tokens"),
    )
    op.create_index(
        "uq_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True
    )
    op.create_index(
        "ix_refresh_tokens_user_session_id", "refresh_tokens", ["user_session_id"]
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("user_sessions")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")

    postgresql.ENUM(name="user_status_enum").drop(op.get_bind(), checkfirst=True)
    op.execute("DROP EXTENSION IF EXISTS citext")
