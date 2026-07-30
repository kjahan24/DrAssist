"""Shared setup helpers for Schedule/Availability module repository
tests — every test needs a real, persisted `organizations` row and a
`doctors` row to satisfy `doctor_availabilities`'/
`doctor_time_off_periods`' foreign keys. Kept local to this test package
rather than in `app/`, matching the identical `persist_organization`/
`persist_doctor` sequence
`tests.integration.modules.appointment._helpers` already established.
"""

from datetime import date
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.infrastructure.repositories import SqlAlchemyDoctorRepository
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
        name="Schedule Test Org",
        type=OrganizationType.CLINIC,
    )
    await repo.add(organization)
    await db_session.commit()
    return organization


async def persist_doctor(db_session: AsyncSession, *, organization_id: object) -> Doctor:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"schedule-test-{_unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Test",
        last_name="Doctor",
    )
    await user_repo.add(user)
    await db_session.commit()

    doctor_repo = SqlAlchemyDoctorRepository(db_session)
    doctor = Doctor.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        user_id=user.id,
        employee_id=f"EMP-{_unique_suffix()}",
        joining_date=date(2026, 1, 1),
    )
    await doctor_repo.add(doctor)
    await db_session.commit()
    return doctor


async def persist_full_chain(db_session: AsyncSession) -> tuple[Organization, Doctor]:
    organization = await persist_organization(db_session)
    doctor = await persist_doctor(db_session, organization_id=organization.id)
    return organization, doctor
