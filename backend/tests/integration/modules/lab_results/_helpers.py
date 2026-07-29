"""Shared setup helpers for Lab Results module repository tests — every
test needs a real, persisted `organizations` row, a `patients` row, a
`doctors` row, a `patient_visits` row, a `clinical_notes` row, a
`lab_orders` row, *and* a `lab_order_items` row (two levels deeper than
`tests.integration.modules.lab_orders._helpers`, since `lab_results`
extends `lab_orders` rather than `clinical_notes` directly, and
`lab_result_items` must reference a real `lab_order_items` row) to
satisfy `lab_results`' foreign keys. Kept local to this test package
rather than in `app/`, matching the identical
`persist_organization`/.../`persist_clinical_note` sequence
`tests.integration.modules.lab_orders._helpers` already established.
"""

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteType
from app.modules.clinical_notes.infrastructure.repositories import (
    SqlAlchemyClinicalNoteRepository,
)
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.infrastructure.repositories import SqlAlchemyDoctorRepository
from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.infrastructure.repositories import (
    SqlAlchemyLabOrderItemRepository,
    SqlAlchemyLabOrderRepository,
)
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
        name="Lab Results Test Org",
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


async def persist_doctor(db_session: AsyncSession, *, organization_id: object) -> Doctor:
    user_repo = SqlAlchemyUserRepository(db_session)
    user = User.register(
        organization_id=organization_id,  # type: ignore[arg-type]
        email=EmailAddress(f"lab-results-test-{_unique_suffix()}@example.com"),
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


async def persist_clinical_note(
    db_session: AsyncSession,
    *,
    organization_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
) -> ClinicalNote:
    repo = SqlAlchemyClinicalNoteRepository(db_session)
    note = ClinicalNote.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        note_number=f"CN-{_unique_suffix()}",
        note_type=ClinicalNoteType.INITIAL,
        encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    await repo.add(note)
    await db_session.commit()
    return note


async def persist_lab_order(
    db_session: AsyncSession,
    *,
    organization_id: object,
    clinical_note_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
) -> LabOrder:
    repo = SqlAlchemyLabOrderRepository(db_session)
    lab_order = LabOrder.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        clinical_note_id=clinical_note_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        order_number=f"LAB-{_unique_suffix()}",
        ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    await repo.add(lab_order)
    await db_session.commit()
    return lab_order


async def persist_lab_order_item(db_session: AsyncSession, *, lab_order_id: object) -> LabOrderItem:
    repo = SqlAlchemyLabOrderItemRepository(db_session)
    item = LabOrderItem.create(
        lab_order_id=lab_order_id,  # type: ignore[arg-type]
        test_code="CBC",
        test_name="Complete Blood Count",
        specimen_type="Blood",
    )
    await repo.add(item)
    await db_session.commit()
    return item


async def persist_full_chain(
    db_session: AsyncSession,
) -> tuple[Organization, Patient, Doctor, PatientVisit, ClinicalNote, LabOrder, LabOrderItem]:
    organization = await persist_organization(db_session)
    patient = await persist_patient(db_session, organization_id=organization.id)
    doctor = await persist_doctor(db_session, organization_id=organization.id)
    visit = await persist_visit(
        db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
    )
    clinical_note = await persist_clinical_note(
        db_session,
        organization_id=organization.id,
        patient_id=patient.id,
        visit_id=visit.id,
        doctor_id=doctor.id,
    )
    lab_order = await persist_lab_order(
        db_session,
        organization_id=organization.id,
        clinical_note_id=clinical_note.id,
        patient_id=patient.id,
        visit_id=visit.id,
        doctor_id=doctor.id,
    )
    lab_order_item = await persist_lab_order_item(db_session, lab_order_id=lab_order.id)
    return organization, patient, doctor, visit, clinical_note, lab_order, lab_order_item
