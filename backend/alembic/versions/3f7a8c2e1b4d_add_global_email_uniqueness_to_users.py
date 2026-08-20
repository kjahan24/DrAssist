"""add global email uniqueness to users

Adds `uq_users_email_global` — a partial unique index on `users.email`
alone (`WHERE deleted_at IS NULL`), alongside the pre-existing
`uq_users_organization_id_email` (organization_id, email) index, which it
does not replace or drop.

Needed for self-service registration/login (`POST /auth/register` /
`POST /auth/login`, `app.modules.authentication.application.use_cases
.register_user`/`.authenticate_user`): both flows resolve a user from
email alone, with no `organization_id` yet known (the current frontend's
Sign Up/Sign In forms collect no organization field at all), so this
migration is what makes "one account per email, system-wide" an enforced
database invariant rather than just an application-level check-then-act
race condition (`UserRepository.get_by_email_any_organization`, in
`app.modules.authentication.infrastructure.repositories`, still performs
the check first — this index is the concurrency safety net under it, the
same "partial unique index backs an application-level check" pattern
`uq_users_organization_id_email` itself already establishes for its own
narrower scope).

No existing table (from any prior phase) is altered beyond this one new
index — `users` itself gains no new column.

Revision ID: 3f7a8c2e1b4d
Revises: 9c4e2a7b1f6d
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f7a8c2e1b4d"
down_revision: str | None = "9c4e2a7b1f6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_users_email_global",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_email_global", table_name="users")
