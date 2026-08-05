"""Shared setup helpers for Community module repository tests — every
test needs a real, persisted `organizations` row, and most also need a
`users` row (community creator / member), to satisfy `communities`'/
`community_members`' required foreign keys. Kept local to this test
package rather than in `app/`, matching the identical
`persist_organization`/`persist_user` sequence
`tests.integration.modules.family_access._helpers` already established.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


def _unique_suffix() -> str:
    return uuid4().hex[:12].upper()


async def persist_organization(db_session: AsyncSession) -> Organization:
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{_unique_suffix()}"),
        name="Community Test Org",
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    await db_session.commit()
    return organization


async def persist_user(db_session: AsyncSession, *, organization_id: object) -> User:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"community-test-{_unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Community",
        last_name="Member",
    )
    await user_repo.add(user)
    await db_session.commit()
    return user


async def persist_organization_and_user(db_session: AsyncSession) -> tuple[Organization, User]:
    organization = await persist_organization(db_session)
    user = await persist_user(db_session, organization_id=organization.id)
    return organization, user
