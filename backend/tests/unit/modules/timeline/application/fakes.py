"""In-memory test doubles for the ten peer modules' public query ports
`TimelineAggregationService`/`TimelineQueryService` depend on — each
implements the exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over
mocks as the default"). Backed by a plain settable list of summary
DTOs (rather than a dict keyed by id) since the primary need here is
"list for patient returns whatever the test seeded", not single-id
lookups.

Each `make_..._summary` builder returns a valid DTO with sensible
defaults for every required field, overridable via kwargs — the same
pattern `tests.unit.modules.appointment.application.fakes
.make_patient_summary` already establishes.
"""

from datetime import date, datetime, time
from uuid import UUID, uuid4

from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.public.dto import AppointmentSummaryDTO
from app.modules.appointment.public.interfaces import AppointmentQueryPort
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.doctor_review.domain.enums import ReviewStatus
from app.modules.doctor_review.public.dto import DoctorReviewSummaryDTO
from app.modules.doctor_review.public.interfaces import DoctorReviewQueryPort
from app.modules.documents.domain.enums import DocumentCategory, DocumentStatus, StorageProvider
from app.modules.documents.public.dto import MedicalDocumentSummaryDTO
from app.modules.documents.public.interfaces import DocumentQueryPort
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.public.dto import LabOrderSummaryDTO
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.domain.enums import LabResultStatus
from app.modules.lab_results.public.dto import LabResultSummaryDTO
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient.domain.enums import (
    AllergySeverity,
    AllergyStatus,
    AllergyType,
    ConditionSeverity,
    ConditionStatus,
    Gender,
    PatientStatus,
)
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.prescriptions.domain.enums import PrescriptionStatus
from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort


def make_appointment_summary(**overrides: object) -> AppointmentSummaryDTO:
    defaults: dict[str, object] = {
        "appointment_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "appointment_number": "APT-0001",
        "appointment_date": date(2026, 1, 1),
        "start_time": time(9, 0),
        "end_time": time(9, 30),
        "appointment_type": AppointmentType.CONSULTATION,
        "status": AppointmentStatus.SCHEDULED,
        "reason_for_visit": None,
        "notes": None,
        "booked_by_user_id": None,
        "visit_id": None,
        "checked_in_at": None,
        "completed_at": None,
        "cancelled_at": None,
    }
    defaults.update(overrides)
    return AppointmentSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_visit_summary(**overrides: object) -> VisitSummaryDTO:
    defaults: dict[str, object] = {
        "visit_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "visit_number": "V-0001",
        "visit_status": VisitStatus.SCHEDULED,
        "visit_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return VisitSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_clinical_note_summary(**overrides: object) -> ClinicalNoteSummaryDTO:
    defaults: dict[str, object] = {
        "clinical_note_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "note_number": "CN-0001",
        "note_type": ClinicalNoteType.INITIAL,
        "status": ClinicalNoteStatus.DRAFT,
        "encounter_datetime": datetime(2026, 1, 1, 9, 0),
        "ai_generated": False,
    }
    defaults.update(overrides)
    return ClinicalNoteSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_soap_note_summary(**overrides: object) -> SOAPNoteSummaryDTO:
    defaults: dict[str, object] = {
        "soap_note_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "chief_complaint": "Headache",
        "history_of_present_illness": None,
        "review_of_systems": None,
        "physical_examination": None,
        "vital_sign_summary": None,
        "assessment": None,
        "plan": None,
    }
    defaults.update(overrides)
    return SOAPNoteSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_prescription_summary(**overrides: object) -> PrescriptionSummaryDTO:
    defaults: dict[str, object] = {
        "prescription_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "prescription_number": "RX-0001",
        "prescription_date": date(2026, 1, 1),
        "status": PrescriptionStatus.DRAFT,
        "notes": None,
        "items": [],
    }
    defaults.update(overrides)
    return PrescriptionSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_lab_order_summary(**overrides: object) -> LabOrderSummaryDTO:
    defaults: dict[str, object] = {
        "lab_order_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "order_number": "LO-0001",
        "ordered_at": datetime(2026, 1, 1, 9, 0),
        "priority": Priority.ROUTINE,
        "status": LabOrderStatus.DRAFT,
        "clinical_information": None,
        "notes": None,
        "items": [],
    }
    defaults.update(overrides)
    return LabOrderSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_lab_result_summary(**overrides: object) -> LabResultSummaryDTO:
    defaults: dict[str, object] = {
        "lab_result_id": uuid4(),
        "organization_id": uuid4(),
        "lab_order_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "result_number": "LR-0001",
        "reported_at": datetime(2026, 1, 1, 9, 0),
        "status": LabResultStatus.DRAFT,
        "laboratory_name": None,
        "comments": None,
        "items": [],
    }
    defaults.update(overrides)
    return LabResultSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_document_summary(**overrides: object) -> MedicalDocumentSummaryDTO:
    defaults: dict[str, object] = {
        "document_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "uploaded_by_user_id": uuid4(),
        "category": DocumentCategory.LAB_REPORT,
        "title": "CBC Panel",
        "original_filename": "cbc.pdf",
        "stored_filename": f"{uuid4().hex}.pdf",
        "mime_type": "application/pdf",
        "extension": ".pdf",
        "file_size_bytes": 2048,
        "storage_provider": StorageProvider.LOCAL,
        "storage_path": f"medical-documents/{uuid4().hex}.pdf",
        "checksum_sha256": "a" * 64,
        "status": DocumentStatus.ACTIVE,
        "uploaded_at": datetime(2026, 1, 1, 9, 0),
        "visit_id": None,
        "appointment_id": None,
        "description": None,
        "tags": None,
        "metadata": None,
    }
    defaults.update(overrides)
    return MedicalDocumentSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_patient_summary(**overrides: object) -> PatientSummaryDTO:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "organization_id": uuid4(),
        "patient_number": "PAT-0001",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1990, 1, 1),
        "status": PatientStatus.ACTIVE,
    }
    defaults.update(overrides)
    return PatientSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_allergy_summary(**overrides: object) -> PatientAllergySummaryDTO:
    defaults: dict[str, object] = {
        "allergy_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "allergy_type": AllergyType.DRUG,
        "allergen_name": "Penicillin",
        "severity": AllergySeverity.SEVERE,
        "reaction": "Anaphylaxis",
        "onset_date": date(2020, 1, 1),
        "status": AllergyStatus.ACTIVE,
        "notes": None,
        "verified_by": None,
        "verified_date": None,
    }
    defaults.update(overrides)
    return PatientAllergySummaryDTO(**defaults)  # type: ignore[arg-type]


def make_condition_summary(**overrides: object) -> PatientMedicalConditionSummaryDTO:
    defaults: dict[str, object] = {
        "condition_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "diagnosed_by": None,
        "condition_name": "Hypertension",
        "icd10_code": None,
        "category": "chronic",
        "severity": ConditionSeverity.MODERATE,
        "diagnosis_date": date(2021, 1, 1),
        "onset_date": None,
        "status": ConditionStatus.ACTIVE,
        "is_chronic": True,
        "is_infectious": False,
        "notes": None,
        "resolved_date": None,
    }
    defaults.update(overrides)
    return PatientMedicalConditionSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_doctor_review_summary(**overrides: object) -> DoctorReviewSummaryDTO:
    defaults: dict[str, object] = {
        "doctor_review_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "clinical_note_id": uuid4(),
        "review_status": ReviewStatus.APPROVED,
        "review_comment": None,
        "reviewed_at": datetime(2026, 1, 1, 9, 0),
        "approved_clinical_note": True,
        "approved_soap_note": True,
        "approved_prescription": True,
        "approved_lab_orders": True,
        "approved_lab_results": True,
        "approved_reasoning": True,
        "approved_differential_diagnosis": True,
        "approved_icd10": True,
    }
    defaults.update(overrides)
    return DoctorReviewSummaryDTO(**defaults)  # type: ignore[arg-type]


class FakeAppointmentQueryPort(AppointmentQueryPort):
    def __init__(self, *, appointments: list[AppointmentSummaryDTO] | None = None) -> None:
        self.appointments = appointments or []

    async def appointment_exists(self, appointment_id: UUID) -> bool:
        return any(a.appointment_id == appointment_id for a in self.appointments)

    async def is_editable(self, appointment_id: UUID) -> bool:
        return True

    async def get_appointment_summary(self, appointment_id: UUID) -> AppointmentSummaryDTO | None:
        return next((a for a in self.appointments if a.appointment_id == appointment_id), None)

    async def get_by_appointment_number(
        self, appointment_number: str
    ) -> AppointmentSummaryDTO | None:
        return next(
            (a for a in self.appointments if a.appointment_number == appointment_number), None
        )

    async def list_appointments_for_patient(self, patient_id: UUID) -> list[AppointmentSummaryDTO]:
        return [a for a in self.appointments if a.patient_id == patient_id]

    async def list_appointments_for_doctor(self, doctor_id: UUID) -> list[AppointmentSummaryDTO]:
        return [a for a in self.appointments if a.doctor_id == doctor_id]


class FakeVisitQueryPort(VisitQueryPort):
    def __init__(self, *, visits: list[VisitSummaryDTO] | None = None) -> None:
        self.visits = visits or []

    async def visit_exists(self, visit_id: UUID) -> bool:
        return any(v.visit_id == visit_id for v in self.visits)

    async def is_active(self, visit_id: UUID) -> bool:
        return True

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        return next((v for v in self.visits if v.visit_id == visit_id), None)

    async def list_visits_for_patient(self, patient_id: UUID) -> list[VisitSummaryDTO]:
        return [v for v in self.visits if v.patient_id == patient_id]


class FakeClinicalNoteQueryPort(ClinicalNoteQueryPort):
    def __init__(self, *, notes: list[ClinicalNoteSummaryDTO] | None = None) -> None:
        self.notes = notes or []

    async def clinical_note_exists(self, clinical_note_id: UUID) -> bool:
        return any(n.clinical_note_id == clinical_note_id for n in self.notes)

    async def is_editable(self, clinical_note_id: UUID) -> bool:
        return True

    async def get_clinical_note_summary(
        self, clinical_note_id: UUID
    ) -> ClinicalNoteSummaryDTO | None:
        return next((n for n in self.notes if n.clinical_note_id == clinical_note_id), None)

    async def list_clinical_notes_for_visit(self, visit_id: UUID) -> list[ClinicalNoteSummaryDTO]:
        return [n for n in self.notes if n.visit_id == visit_id]

    async def list_clinical_notes_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalNoteSummaryDTO]:
        return [n for n in self.notes if n.patient_id == patient_id]


class FakeSOAPNoteQueryPort(SOAPNoteQueryPort):
    def __init__(self, *, soap_notes: list[SOAPNoteSummaryDTO] | None = None) -> None:
        self.soap_notes = soap_notes or []

    async def soap_note_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return any(s.clinical_note_id == clinical_note_id for s in self.soap_notes)

    async def get_soap_note_summary(self, clinical_note_id: UUID) -> SOAPNoteSummaryDTO | None:
        return next((s for s in self.soap_notes if s.clinical_note_id == clinical_note_id), None)


class FakePrescriptionQueryPort(PrescriptionQueryPort):
    def __init__(self, *, prescriptions: list[PrescriptionSummaryDTO] | None = None) -> None:
        self.prescriptions = prescriptions or []

    async def prescription_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return any(p.clinical_note_id == clinical_note_id for p in self.prescriptions)

    async def get_prescription_summary(
        self, clinical_note_id: UUID
    ) -> PrescriptionSummaryDTO | None:
        return next((p for p in self.prescriptions if p.clinical_note_id == clinical_note_id), None)

    async def list_prescriptions_for_patient(
        self, patient_id: UUID
    ) -> list[PrescriptionSummaryDTO]:
        return [p for p in self.prescriptions if p.patient_id == patient_id]


class FakeLabOrderQueryPort(LabOrderQueryPort):
    def __init__(self, *, lab_orders: list[LabOrderSummaryDTO] | None = None) -> None:
        self.lab_orders = lab_orders or []

    async def lab_order_exists(self, lab_order_id: UUID) -> bool:
        return any(o.lab_order_id == lab_order_id for o in self.lab_orders)

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return True

    async def get_lab_order_summary(self, lab_order_id: UUID) -> LabOrderSummaryDTO | None:
        return next((o for o in self.lab_orders if o.lab_order_id == lab_order_id), None)

    async def list_lab_orders_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[LabOrderSummaryDTO]:
        return [o for o in self.lab_orders if o.clinical_note_id == clinical_note_id]

    async def list_lab_orders_for_patient(self, patient_id: UUID) -> list[LabOrderSummaryDTO]:
        return [o for o in self.lab_orders if o.patient_id == patient_id]


class FakeLabResultQueryPort(LabResultQueryPort):
    def __init__(self, *, lab_results: list[LabResultSummaryDTO] | None = None) -> None:
        self.lab_results = lab_results or []

    async def lab_result_exists_for_lab_order(self, lab_order_id: UUID) -> bool:
        return any(r.lab_order_id == lab_order_id for r in self.lab_results)

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return True

    async def get_lab_result_summary(self, lab_order_id: UUID) -> LabResultSummaryDTO | None:
        return next((r for r in self.lab_results if r.lab_order_id == lab_order_id), None)

    async def list_lab_results_for_patient(self, patient_id: UUID) -> list[LabResultSummaryDTO]:
        return [r for r in self.lab_results if r.patient_id == patient_id]


class FakeDocumentQueryPort(DocumentQueryPort):
    def __init__(self, *, documents: list[MedicalDocumentSummaryDTO] | None = None) -> None:
        self.documents = documents or []

    async def document_exists(self, document_id: UUID) -> bool:
        return any(d.document_id == document_id for d in self.documents)

    async def get_document_summary(self, document_id: UUID) -> MedicalDocumentSummaryDTO | None:
        return next((d for d in self.documents if d.document_id == document_id), None)

    async def list_documents_for_patient(self, patient_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        return [d for d in self.documents if d.patient_id == patient_id]

    async def list_documents_for_visit(self, visit_id: UUID) -> list[MedicalDocumentSummaryDTO]:
        return [d for d in self.documents if d.visit_id == visit_id]

    async def list_documents_for_appointment(
        self, appointment_id: UUID
    ) -> list[MedicalDocumentSummaryDTO]:
        return [d for d in self.documents if d.appointment_id == appointment_id]


class FakePatientQueryPort(PatientQueryPort):
    def __init__(
        self,
        *,
        patients: list[PatientSummaryDTO] | None = None,
        allergies: list[PatientAllergySummaryDTO] | None = None,
        conditions: list[PatientMedicalConditionSummaryDTO] | None = None,
    ) -> None:
        self.patients = patients or []
        self.allergies = allergies or []
        self.conditions = conditions or []

    async def patient_exists(self, patient_id: UUID) -> bool:
        return any(p.patient_id == patient_id for p in self.patients)

    async def is_active(self, patient_id: UUID) -> bool:
        return True

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        return next((p for p in self.patients if p.patient_id == patient_id), None)

    async def list_allergies_for_patient(self, patient_id: UUID) -> list[PatientAllergySummaryDTO]:
        return [a for a in self.allergies if a.patient_id == patient_id]

    async def list_medical_conditions_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicalConditionSummaryDTO]:
        return [c for c in self.conditions if c.patient_id == patient_id]


class FakeDoctorReviewQueryPort(DoctorReviewQueryPort):
    def __init__(self, *, reviews: list[DoctorReviewSummaryDTO] | None = None) -> None:
        self.reviews = reviews or []

    async def doctor_review_exists(self, doctor_review_id: UUID) -> bool:
        return any(r.doctor_review_id == doctor_review_id for r in self.reviews)

    async def is_editable(self, doctor_review_id: UUID) -> bool:
        return True

    async def get_doctor_review_summary(
        self, doctor_review_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        return next((r for r in self.reviews if r.doctor_review_id == doctor_review_id), None)

    async def get_doctor_review_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        return next((r for r in self.reviews if r.clinical_note_id == clinical_note_id), None)

    async def list_doctor_reviews_for_patient(
        self, patient_id: UUID
    ) -> list[DoctorReviewSummaryDTO]:
        return [r for r in self.reviews if r.patient_id == patient_id]
