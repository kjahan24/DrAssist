"""Shared setup helpers for Family / Caregiver Access module repository
tests — every test needs a real, persisted `organizations` row, a
`patients` row, and a `users` row (the caregiver) to satisfy
`family_access_grants`' required foreign keys. Kept local to this test
package rather than in `app/`, matching the identical
`persist_organization`/`persist_patient`/`persist_user` sequence
`tests.integration.modules.appointment._helpers` already established.
"""

from datetime import date
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientRepository
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


def _unique_suffix() -> str:
    return uuid4().hex[:12].upper()


async def persist_organization(db_session: AsyncSession) -> Organization:
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{_unique_suffix()}"),
        name="Family Access Test Org",
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    await db_session.commit()
    return organization


async def persist_patient(db_session: AsyncSession, *, organization_id: object) -> Patient:
    repo = SqlAlchemyPatientRepository(db_session)
    patient = Patient.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_number=f"PAT-{_unique_suffix()}",
        first_name="Jane",
        last_name="Doe",
        gender=Gender.FEMALE,
        date_of_birth=date(1990, 1, 1),
    )
    await repo.add(patient)
    await db_session.commit()
    return patient


async def persist_user(db_session: AsyncSession, *, organization_id: object) -> User:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"family-access-test-{_unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Cara",
        last_name="Giver",
    )
    await user_repo.add(user)
    await db_session.commit()
    return user


async def persist_full_chain(db_session: AsyncSession) -> tuple[Organization, Patient, User]:
    organization = await persist_organization(db_session)
    patient = await persist_patient(db_session, organization_id=organization.id)
    caregiver = await persist_user(db_session, organization_id=organization.id)
    return organization, patient, caregiver
