"""Shared setup helpers for Documents module repository tests — every
test needs a real, persisted `organizations` row, a `patients` row, and a
`users` row to satisfy `medical_documents`' required foreign keys;
`persist_visit` and `persist_appointment` additionally support the tests
exercising `visit_id`/`appointment_id`. Kept local to this test package
rather than in `app/`, matching the identical
`persist_organization`/`persist_patient`/`persist_doctor`/`persist_visit`
sequence `tests.integration.modules.attachments._helpers` already
established.
"""

from datetime import date, time
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentType
from app.modules.appointment.infrastructure.repositories import SqlAlchemyAppointmentRepository
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
from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.enums import VisitType
from app.modules.visit.infrastructure.repositories import SqlAlchemyPatientVisitRepository
from app.shared.domain.common_value_objects import EmailAddress

_PLACEHOLDER_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


def _unique_suffix() -> str:
    return uuid4().hex[:12].upper()


async def persist_organization(db_session: AsyncSession) -> Organization:
    repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(f"ORG-{_unique_suffix()}"),
        name="Documents Test Org",
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
        email=EmailAddress(f"documents-test-{_unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Test",
        last_name="Uploader",
    )
    await user_repo.add(user)
    await db_session.commit()
    return user


async def persist_doctor(db_session: AsyncSession, *, organization_id: object) -> Doctor:
    user = await persist_user(db_session, organization_id=organization_id)

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


async def persist_visit(
    db_session: AsyncSession, *, organization_id: object, patient_id: object, doctor_id: object
) -> PatientVisit:
    repo = SqlAlchemyPatientVisitRepository(db_session)
    visit = PatientVisit.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        visit_number=f"V-{_unique_suffix()}",
        visit_type=VisitType.CONSULTATION,
        visit_date=date(2026, 1, 1),
    )
    await repo.add(visit)
    await db_session.commit()
    return visit


async def persist_appointment(
    db_session: AsyncSession, *, organization_id: object, patient_id: object, doctor_id: object
) -> Appointment:
    repo = SqlAlchemyAppointmentRepository(db_session)
    appointment = Appointment.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        appointment_number=f"APT-{_unique_suffix()}",
        appointment_date=date(2026, 1, 1),
        start_time=time(9, 0),
        end_time=time(9, 30),
        appointment_type=AppointmentType.CONSULTATION,
    )
    await repo.add(appointment)
    await db_session.commit()
    return appointment


async def persist_full_chain(
    db_session: AsyncSession,
) -> tuple[Organization, Patient, User, Doctor, PatientVisit, Appointment]:
    organization = await persist_organization(db_session)
    patient = await persist_patient(db_session, organization_id=organization.id)
    user = await persist_user(db_session, organization_id=organization.id)
    doctor = await persist_doctor(db_session, organization_id=organization.id)
    visit = await persist_visit(
        db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
    )
    appointment = await persist_appointment(
        db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
    )
    return organization, patient, user, doctor, visit, appointment
