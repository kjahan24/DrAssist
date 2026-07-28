"""Shared setup helper for Patient module repository tests — every test
needs a real, persisted `organizations` row to satisfy
`patients.organization_id`'s foreign key. Kept local to this test package
rather than in `app/`, matching the identical
`tests.integration.modules.doctor._helpers.persist_organization`.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository


async def persist_organization(db_session: AsyncSession) -> Organization:
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{uuid4().hex[:12].upper()}"),
        name="Patient Test Org",
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    await db_session.commit()
    return organization
