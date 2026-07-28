"""Shared setup helpers for Patient module repository tests — every test
needs a real, persisted `organizations` row to satisfy
`patients.organization_id`'s foreign key, the Patient Contacts tests
additionally need a real, persisted `patients` row to satisfy their own
`patient_id` foreign keys, and the Patient Allergies tests additionally
need a real, persisted `doctors` row to satisfy `verified_by`'s foreign
key. Kept local to this test package rather than in `app/`, matching the
identical `tests.integration.modules.doctor._helpers.persist_organization`
(the `persist_doctor` helper below mirrors that file's own
`persist_organization`/`persist_user` + doctor-creation sequence, since
patient_allergies tests need a real doctor the same way doctor tests need
a real organization/user).
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
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientRepository
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


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


async def persist_patient(db_session: AsyncSession) -> Patient:
    organization = await persist_organization(db_session)
    repo = SqlAlchemyPatientRepository(db_session)
    patient = Patient.register(
        organization_id=organization.id,
        patient_number=f"PAT-{uuid4().hex[:12].upper()}",
        first_name="Jane",
        last_name="Doe",
        gender=Gender.FEMALE,
        date_of_birth=date(1990, 1, 1),
    )
    await repo.add(patient)
    await db_session.commit()
    return patient


async def persist_doctor(db_session: AsyncSession, *, organization_id: object) -> Doctor:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"allergy-test-{uuid4().hex[:12]}@example.com"),
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
        employee_id=f"EMP-{uuid4().hex[:12].upper()}",
        joining_date=date(2026, 1, 1),
    )
    await doctor_repo.add(doctor)
    await db_session.commit()
    return doctor
