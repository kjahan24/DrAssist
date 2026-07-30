"""extend roles and permissions for rbac

A later task ("Implement the RBAC (Roles & Permissions) module") found
`roles`/`permissions`/`role_permissions`/`user_roles` already created by
`dd4c7542b13e_create_authentication_tables` and, rather than forking a
second, disconnected permission system under new tables, extended these
two tables in place — see `app.modules.authentication.infrastructure
.models` and `.container`'s own notes on this decision. This migration
never edits `dd4c7542b13e` itself (per this task's own "do not modify
existing migrations" rule); it only adds a new revision on top of it.

`roles.is_active` — new nullable-free `BOOLEAN NOT NULL DEFAULT true`
column: every pre-existing row (if any existed) becomes active, matching
`Role.is_active`'s own default. `roles` also gains a same-row `CHECK`
constraint mirroring `Role.__post_init__`'s "global system roles must
have organization_id = NULL" / "organization roles must belong to
exactly one organization" invariant — both halves live on this one row,
so (unlike "valid status transitions" elsewhere in this codebase, which
need the *previous* row and can't be a `CHECK`) this one can be, and is,
enforced at both layers for defense-in-depth.

`permissions.module` is renamed to `resource` — an exact rename, not a
new parallel column: `module` and `resource` name the same concept, so
keeping both would only add confusing, redundant schema (see
`app.modules.authentication.domain.entities.Permission`'s own docstring
for why `resource`/`action` are derived from `code` rather than
independently supplied). `permissions.name` and `permissions.action` are
added `NOT NULL` with no backfill step: `permissions` was provably empty
before this migration — no application code path ever inserted a row
into it (`CreatePermission`, added by this same task, is the first one
that does) — so there is no existing data to backfill.
`permissions.description` becomes nullable, matching this task's own
field spec (previously `NOT NULL`, an artifact of the original
Authentication task predating this one).

Revision ID: b22ab71b3d39
Revises: 8a5985e065f3
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b22ab71b3d39"
down_revision: str | None = "8a5985e065f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- roles: is_active + system-role/organization-scope CHECK --------
    op.add_column(
        "roles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_check_constraint(
        "system_role_organization_scope",
        "roles",
        "(is_system_role = true AND organization_id IS NULL) OR "
        "(is_system_role = false AND organization_id IS NOT NULL)",
    )

    # --- permissions: module -> resource, + name/action, description nullable
    op.alter_column("permissions", "module", new_column_name="resource", existing_type=sa.Text())
    op.add_column("permissions", sa.Column("name", sa.Text(), nullable=False))
    op.add_column("permissions", sa.Column("action", sa.Text(), nullable=False))
    op.alter_column("permissions", "description", existing_type=sa.Text(), nullable=True)

    op.drop_index("ix_permissions_module", table_name="permissions")
    op.create_index("ix_permissions_resource_action", "permissions", ["resource", "action"])


def downgrade() -> None:
    op.drop_index("ix_permissions_resource_action", table_name="permissions")

    op.alter_column("permissions", "description", existing_type=sa.Text(), nullable=False)
    op.drop_column("permissions", "action")
    op.drop_column("permissions", "name")
    op.alter_column("permissions", "resource", new_column_name="module", existing_type=sa.Text())

    op.create_index("ix_permissions_module", "permissions", ["module"])

    # `op.drop_constraint` re-applies the naming convention to whatever
    # name it's given (the same "bare token, not the fully-qualified
    # name" rule `dd4c7542b13e`'s own `failed_login_attempts_nonneg`
    # comment documents for `create`) — passing the already-prefixed
    # `ck_roles_system_role_organization_scope` here doubles the prefix
    # into `ck_roles_ck_roles_...`, confirmed against a real Postgres
    # instance while building this migration.
    op.drop_constraint("system_role_organization_scope", "roles", type_="check")
    op.drop_column("roles", "is_active")
