"""Shared setup helpers for Medical Topics module repository tests —
`medical_topics.created_by`/`updated_by` and `medical_topic_followers
.user_id` all require a real, persisted `users` row (which itself
requires an `organizations` row) to satisfy their FKs. Kept local to
this test package rather than in `app/`, matching the identical
`persist_organization`/`persist_user` sequence
`tests.integration.modules.community._helpers` already established.
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


def unique_suffix() -> str:
    return uuid4().hex[:12]


async def persist_user(db_session: AsyncSession) -> User:
    org_repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{unique_suffix()}"),
        name="Medical Topics Test Org",
        type=OrganizationType.CLINIC,
    )
    await org_repo.add(organization)
    await db_session.commit()

    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization.id,
        email=EmailAddress(f"medical-topics-test-{unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Topics",
        last_name="Tester",
    )
    await user_repo.add(user)
    await db_session.commit()
    return user
