"""Shared setup helpers for Patient module repository tests — every test
needs a real, persisted `organizations` row to satisfy
`patients.organization_id`'s foreign key, and the Patient Contacts tests
additionally need a real, persisted `patients` row to satisfy their own
`patient_id` foreign keys. Kept local to this test package rather than in
`app/`, matching the identical
`tests.integration.modules.doctor._helpers.persist_organization`.
"""

from datetime import date
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientRepository


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
