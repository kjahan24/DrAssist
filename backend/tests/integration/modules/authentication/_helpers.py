"""Shared setup helpers for Authentication module RBAC repository tests.

`organization_id` columns on `users`/`roles`/`user_roles` carry no
foreign key to `organizations` (see `app.modules.authentication
.infrastructure.models`'s own note — deferred when the Organization
module didn't exist yet, and not revisited by this task, which is scoped
to RBAC only), so a bare `uuid4()` is a valid `organization_id` for every
helper below — no `organizations` row needs to exist first.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


def unique_suffix() -> str:
    return uuid4().hex[:12]


async def persist_user(db_session: AsyncSession, *, organization_id: object) -> User:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"rbac-test-{unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Test",
        last_name="User",
    )
    await user_repo.add(user)
    await db_session.commit()
    return user
