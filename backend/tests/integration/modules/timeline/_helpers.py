"""Shared setup helpers for Timeline module integration tests — a full
patient chain across every one of the ten peer modules
`TimelineAggregationService` reads from, so a single test can exercise a
real cross-module aggregation against real PostgreSQL. Kept local to
this test package rather than in `app/`, matching the identical
`persist_organization`/`persist_patient`/`persist_doctor`/`persist_visit`
sequence `tests.integration.modules.documents._helpers` already
established (the first six helpers below are that same sequence, plus
`persist_appointment`; the rest are new to this package).
"""

from datetime import UTC, date, datetime, time
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentType
from app.modules.appointment.infrastructure.repositories import SqlAlchemyAppointmentRepository
from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteType
from app.modules.clinical_notes.infrastructure.repositories import SqlAlchemyClinicalNoteRepository
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.infrastructure.repositories import SqlAlchemyDoctorRepository
from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.infrastructure.repositories import SqlAlchemyDoctorReviewRepository
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.enums import DocumentCategory, StorageProvider
from app.modules.documents.domain.value_objects import Sha256Checksum
from app.modules.documents.infrastructure.repositories import SqlAlchemyMedicalDocumentRepository
from app.modules.lab_orders.domain.entities import LabOrder
from app.modules.lab_orders.infrastructure.repositories import SqlAlchemyLabOrderRepository
from app.modules.lab_results.domain.entities import LabResult
from app.modules.lab_results.infrastructure.repositories import SqlAlchemyLabResultRepository
from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository
from app.modules.patient.domain.entities import (
    Patient,
    PatientAllergy,
    PatientMedicalCondition,
)
from app.modules.patient.domain.enums import (
    AllergySeverity,
    AllergyType,
    ConditionSeverity,
    Gender,
)
from app.modules.patient.infrastructure.repositories import (
    SqlAlchemyPatientAllergyRepository,
    SqlAlchemyPatientMedicalConditionRepository,
    SqlAlchemyPatientRepository,
)
from app.modules.prescriptions.domain.entities import Prescription
from app.modules.prescriptions.infrastructure.repositories import SqlAlchemyPrescriptionRepository
from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.infrastructure.repositories import SqlAlchemySOAPNoteRepository
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
        name="Timeline Test Org",
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
        email=EmailAddress(f"timeline-test-{_unique_suffix()}@example.com"),
        password_hash=_PLACEHOLDER_PASSWORD_HASH,
        first_name="Test",
        last_name="User",
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


async def persist_clinical_note(
    db_session: AsyncSession,
    *,
    organization_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
    encounter_datetime: datetime = datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
) -> ClinicalNote:
    repo = SqlAlchemyClinicalNoteRepository(db_session)
    note = ClinicalNote.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        note_number=f"CN-{_unique_suffix()}",
        note_type=ClinicalNoteType.INITIAL,
        encounter_datetime=encounter_datetime,
        chief_complaint_summary="Headache",
    )
    await repo.add(note)
    await db_session.commit()
    return note


async def persist_soap_note(
    db_session: AsyncSession,
    *,
    organization_id: object,
    clinical_note_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
) -> SOAPNote:
    repo = SqlAlchemySOAPNoteRepository(db_session)
    soap_note = SOAPNote.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        clinical_note_id=clinical_note_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        chief_complaint="Headache, 2 days",
    )
    await repo.add(soap_note)
    await db_session.commit()
    return soap_note


async def persist_prescription(
    db_session: AsyncSession,
    *,
    organization_id: object,
    clinical_note_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
    prescription_date: date = date(2026, 1, 1),
) -> Prescription:
    repo = SqlAlchemyPrescriptionRepository(db_session)
    prescription = Prescription.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        clinical_note_id=clinical_note_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        prescription_number=f"RX-{_unique_suffix()}",
        prescription_date=prescription_date,
    )
    await repo.add(prescription)
    await db_session.commit()
    return prescription


async def persist_lab_order(
    db_session: AsyncSession,
    *,
    organization_id: object,
    clinical_note_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
    ordered_at: datetime = datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
) -> LabOrder:
    repo = SqlAlchemyLabOrderRepository(db_session)
    lab_order = LabOrder.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        clinical_note_id=clinical_note_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        order_number=f"LO-{_unique_suffix()}",
        ordered_at=ordered_at,
    )
    await repo.add(lab_order)
    await db_session.commit()
    return lab_order


async def persist_lab_result(
    db_session: AsyncSession,
    *,
    organization_id: object,
    lab_order_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
    reported_at: datetime = datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
) -> LabResult:
    repo = SqlAlchemyLabResultRepository(db_session)
    lab_result = LabResult.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        lab_order_id=lab_order_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        result_number=f"LR-{_unique_suffix()}",
        reported_at=reported_at,
    )
    await repo.add(lab_result)
    await db_session.commit()
    return lab_result


async def persist_document(
    db_session: AsyncSession,
    *,
    organization_id: object,
    patient_id: object,
    uploaded_by_user_id: object,
    visit_id: object | None = None,
    uploaded_at: datetime = datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
) -> MedicalDocument:
    repo = SqlAlchemyMedicalDocumentRepository(db_session)
    document = MedicalDocument.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        uploaded_by_user_id=uploaded_by_user_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        category=DocumentCategory.LAB_REPORT,
        title="CBC Panel",
        original_filename="cbc.pdf",
        stored_filename=f"{uuid4().hex}.pdf",
        mime_type="application/pdf",
        extension=".pdf",
        file_size_bytes=2048,
        storage_provider=StorageProvider.LOCAL,
        storage_path=f"medical-documents/{uuid4().hex}.pdf",
        checksum_sha256=Sha256Checksum((uuid4().hex + uuid4().hex)[:64]),
        uploaded_at=uploaded_at,
    )
    document.activate()
    await repo.add(document)
    await db_session.commit()
    return document


async def persist_allergy(
    db_session: AsyncSession,
    *,
    organization_id: object,
    patient_id: object,
    onset_date: date = date(2020, 1, 1),
) -> PatientAllergy:
    repo = SqlAlchemyPatientAllergyRepository(db_session)
    allergy = PatientAllergy.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        allergy_type=AllergyType.DRUG,
        allergen_name="Penicillin",
        severity=AllergySeverity.SEVERE,
        reaction="Anaphylaxis",
        onset_date=onset_date,
    )
    await repo.add(allergy)
    await db_session.commit()
    return allergy


async def persist_condition(
    db_session: AsyncSession,
    *,
    organization_id: object,
    patient_id: object,
    diagnosis_date: date = date(2021, 1, 1),
) -> PatientMedicalCondition:
    repo = SqlAlchemyPatientMedicalConditionRepository(db_session)
    condition = PatientMedicalCondition.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        condition_name="Hypertension",
        category="chronic",
        severity=ConditionSeverity.MODERATE,
        diagnosis_date=diagnosis_date,
        is_chronic=True,
    )
    await repo.add(condition)
    await db_session.commit()
    return condition


async def persist_doctor_review(
    db_session: AsyncSession,
    *,
    organization_id: object,
    patient_id: object,
    visit_id: object,
    doctor_id: object,
    clinical_note_id: object,
    approve: bool = True,
) -> DoctorReview:
    repo = SqlAlchemyDoctorReviewRepository(db_session)
    review = DoctorReview.create(
        organization_id=organization_id,  # type: ignore[arg-type]
        patient_id=patient_id,  # type: ignore[arg-type]
        visit_id=visit_id,  # type: ignore[arg-type]
        doctor_id=doctor_id,  # type: ignore[arg-type]
        clinical_note_id=clinical_note_id,  # type: ignore[arg-type]
    )
    if approve:
        review.approve()
    await repo.add(review)
    await db_session.commit()
    return review
