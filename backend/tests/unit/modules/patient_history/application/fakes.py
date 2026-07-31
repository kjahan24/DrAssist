"""In-memory test doubles for the Patient History module's repository,
Unit of Work, and the eight peer modules' public ports `CreatePatientHistory`
and `PatientHistoryReferenceValidator` depend on — each implements the
exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource
from app.modules.differential_diagnosis.domain.enums import ReviewStatus as DiagnosisReviewStatus
from app.modules.differential_diagnosis.public.dto import DifferentialDiagnosisSummaryDTO
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.doctor_review.application.dto import DoctorReviewSummaryDTO
from app.modules.doctor_review.domain.enums import ReviewStatus as DoctorReviewStatus
from app.modules.doctor_review.public.interfaces import DoctorReviewQueryPort
from app.modules.icd10_coding.domain.enums import CodingSource
from app.modules.icd10_coding.domain.enums import ReviewStatus as ICD10ReviewStatus
from app.modules.icd10_coding.public.dto import ICD10CodingSummaryDTO
from app.modules.icd10_coding.public.interfaces import ICD10CodingQueryPort
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.public.dto import LabOrderSummaryDTO
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.domain.enums import LabResultStatus
from app.modules.lab_results.public.dto import LabResultSummaryDTO
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from app.modules.patient_history.domain.repositories import PatientHistoryRepository
from app.modules.prescriptions.domain.enums import PrescriptionStatus
from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakePatientHistoryRepository(PatientHistoryRepository):
    def __init__(self) -> None:
        self._history: dict[UUID, PatientHistory] = {}

    async def get_by_id(self, patient_history_id: UUID) -> PatientHistory | None:
        return self._history.get(patient_history_id)

    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistory | None:
        for history in self._history.values():
            if history.reference_type == reference_type and history.reference_id == reference_id:
                return history
        return None

    async def list_by_patient(self, patient_id: UUID) -> list[PatientHistory]:
        matches = [h for h in self._history.values() if h.patient_id == patient_id]
        return sorted(matches, key=lambda h: h.encounter_date)

    async def list_by_visit(self, visit_id: UUID) -> list[PatientHistory]:
        matches = [h for h in self._history.values() if h.visit_id == visit_id]
        return sorted(matches, key=lambda h: h.encounter_date)

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        history_types: Sequence[HistoryType] | None = None,
        reference_types: Sequence[ReferenceType] | None = None,
        patient_id: UUID | None = None,
        visit_id: UUID | None = None,
        doctor_review_id: UUID | None = None,
        reference_id: UUID | None = None,
        encounter_date_from: date | None = None,
        encounter_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[PatientHistory], int]:
        matches = [h for h in self._history.values() if h.organization_id == organization_id]
        if history_types:
            matches = [h for h in matches if h.history_type in history_types]
        if reference_types:
            matches = [h for h in matches if h.reference_type in reference_types]
        if patient_id is not None:
            matches = [h for h in matches if h.patient_id == patient_id]
        if visit_id is not None:
            matches = [h for h in matches if h.visit_id == visit_id]
        if doctor_review_id is not None:
            matches = [h for h in matches if h.doctor_review_id == doctor_review_id]
        if reference_id is not None:
            matches = [h for h in matches if h.reference_id == reference_id]
        if encounter_date_from is not None:
            matches = [h for h in matches if h.encounter_date >= encounter_date_from]
        if encounter_date_to is not None:
            matches = [h for h in matches if h.encounter_date <= encounter_date_to]
        if created_from is not None:
            matches = [h for h in matches if h.created_at >= created_from]
        if created_to is not None:
            matches = [h for h in matches if h.created_at <= created_to]
        if updated_from is not None:
            matches = [h for h in matches if h.updated_at >= updated_from]
        if updated_to is not None:
            matches = [h for h in matches if h.updated_at <= updated_to]
        if query:
            term = query.strip().lower()
            matches = [h for h in matches if term in h.summary.lower()]
        matches.sort(key=lambda h: getattr(h, sort_by, None) or "", reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, history: PatientHistory) -> None:
        self._history[history.id] = history


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass


class FakeDoctorReviewQueryPort(DoctorReviewQueryPort):
    def __init__(
        self, *, existing_reviews: dict[UUID, DoctorReviewSummaryDTO] | None = None
    ) -> None:
        self.existing_reviews = existing_reviews or {}

    async def doctor_review_exists(self, doctor_review_id: UUID) -> bool:
        return doctor_review_id in self.existing_reviews

    async def is_editable(self, doctor_review_id: UUID) -> bool:
        return False

    async def get_doctor_review_summary(
        self, doctor_review_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        return self.existing_reviews.get(doctor_review_id)

    async def get_doctor_review_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        for review in self.existing_reviews.values():
            if review.clinical_note_id == clinical_note_id:
                return review
        return None

    async def list_doctor_reviews_for_patient(
        self, patient_id: UUID
    ) -> list[DoctorReviewSummaryDTO]:
        return [r for r in self.existing_reviews.values() if r.patient_id == patient_id]


class FakeClinicalNoteQueryPort(ClinicalNoteQueryPort):
    def __init__(self, *, existing_notes: dict[UUID, ClinicalNoteSummaryDTO] | None = None) -> None:
        self.existing_notes = existing_notes or {}

    async def clinical_note_exists(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.existing_notes

    async def is_editable(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.existing_notes

    async def get_clinical_note_summary(
        self, clinical_note_id: UUID
    ) -> ClinicalNoteSummaryDTO | None:
        return self.existing_notes.get(clinical_note_id)

    async def list_clinical_notes_for_visit(self, visit_id: UUID) -> list[ClinicalNoteSummaryDTO]:
        return [n for n in self.existing_notes.values() if n.visit_id == visit_id]

    async def list_clinical_notes_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalNoteSummaryDTO]:
        return [n for n in self.existing_notes.values() if n.patient_id == patient_id]


class FakeSOAPNoteQueryPort(SOAPNoteQueryPort):
    def __init__(
        self, *, summary_by_clinical_note: dict[UUID, SOAPNoteSummaryDTO] | None = None
    ) -> None:
        self.summary_by_clinical_note = summary_by_clinical_note or {}

    async def soap_note_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.summary_by_clinical_note

    async def get_soap_note_summary(self, clinical_note_id: UUID) -> SOAPNoteSummaryDTO | None:
        return self.summary_by_clinical_note.get(clinical_note_id)


class FakePrescriptionQueryPort(PrescriptionQueryPort):
    def __init__(
        self, *, summary_by_clinical_note: dict[UUID, PrescriptionSummaryDTO] | None = None
    ) -> None:
        self.summary_by_clinical_note = summary_by_clinical_note or {}

    async def prescription_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.summary_by_clinical_note

    async def get_prescription_summary(
        self, clinical_note_id: UUID
    ) -> PrescriptionSummaryDTO | None:
        return self.summary_by_clinical_note.get(clinical_note_id)

    async def list_prescriptions_for_patient(
        self, patient_id: UUID
    ) -> list[PrescriptionSummaryDTO]:
        return []


class FakeLabOrderQueryPort(LabOrderQueryPort):
    def __init__(
        self,
        *,
        lab_orders_by_id: dict[UUID, LabOrderSummaryDTO] | None = None,
        lab_orders_by_clinical_note: dict[UUID, list[LabOrderSummaryDTO]] | None = None,
    ) -> None:
        self.lab_orders_by_id = lab_orders_by_id or {}
        self.lab_orders_by_clinical_note = lab_orders_by_clinical_note or {}

    async def lab_order_exists(self, lab_order_id: UUID) -> bool:
        return lab_order_id in self.lab_orders_by_id

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return False

    async def get_lab_order_summary(self, lab_order_id: UUID) -> LabOrderSummaryDTO | None:
        return self.lab_orders_by_id.get(lab_order_id)

    async def list_lab_orders_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[LabOrderSummaryDTO]:
        return self.lab_orders_by_clinical_note.get(clinical_note_id, [])

    async def list_lab_orders_for_patient(self, patient_id: UUID) -> list[LabOrderSummaryDTO]:
        return []


class FakeLabResultQueryPort(LabResultQueryPort):
    def __init__(
        self, *, results_by_lab_order: dict[UUID, LabResultSummaryDTO] | None = None
    ) -> None:
        self.results_by_lab_order = results_by_lab_order or {}

    async def lab_result_exists_for_lab_order(self, lab_order_id: UUID) -> bool:
        return lab_order_id in self.results_by_lab_order

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return False

    async def get_lab_result_summary(self, lab_order_id: UUID) -> LabResultSummaryDTO | None:
        return self.results_by_lab_order.get(lab_order_id)

    async def list_lab_results_for_patient(self, patient_id: UUID) -> list[LabResultSummaryDTO]:
        return []


class FakeDifferentialDiagnosisQueryPort(DifferentialDiagnosisQueryPort):
    def __init__(
        self,
        *,
        existing_records: dict[UUID, DifferentialDiagnosisSummaryDTO] | None = None,
    ) -> None:
        self.existing_records = existing_records or {}

    async def differential_diagnosis_exists(self, differential_diagnosis_id: UUID) -> bool:
        return differential_diagnosis_id in self.existing_records

    async def is_editable(self, differential_diagnosis_id: UUID) -> bool:
        return False

    async def get_differential_diagnosis_summary(
        self, differential_diagnosis_id: UUID
    ) -> DifferentialDiagnosisSummaryDTO | None:
        return self.existing_records.get(differential_diagnosis_id)

    async def list_differential_diagnoses_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        return [r for r in self.existing_records.values() if r.clinical_note_id == clinical_note_id]

    async def list_differential_diagnoses_for_patient(
        self, patient_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        return []


class FakeICD10CodingQueryPort(ICD10CodingQueryPort):
    def __init__(
        self, *, existing_codings: dict[UUID, ICD10CodingSummaryDTO] | None = None
    ) -> None:
        self.existing_codings = existing_codings or {}

    async def icd10_coding_exists(self, icd10_coding_id: UUID) -> bool:
        return icd10_coding_id in self.existing_codings

    async def is_editable(self, icd10_coding_id: UUID) -> bool:
        return False

    async def get_icd10_coding_summary(self, icd10_coding_id: UUID) -> ICD10CodingSummaryDTO | None:
        return self.existing_codings.get(icd10_coding_id)

    async def get_primary_icd10_coding_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> ICD10CodingSummaryDTO | None:
        return None

    async def list_icd10_codings_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ICD10CodingSummaryDTO]:
        return [c for c in self.existing_codings.values() if c.clinical_note_id == clinical_note_id]

    async def list_icd10_codings_for_patient(self, patient_id: UUID) -> list[ICD10CodingSummaryDTO]:
        return []


def make_doctor_review_summary(**overrides: object) -> DoctorReviewSummaryDTO:
    defaults: dict[str, object] = {
        "doctor_review_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "clinical_note_id": uuid4(),
        "review_status": DoctorReviewStatus.APPROVED,
        "review_comment": None,
        "reviewed_at": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        "approved_clinical_note": True,
        "approved_soap_note": False,
        "approved_prescription": False,
        "approved_lab_orders": False,
        "approved_lab_results": False,
        "approved_reasoning": False,
        "approved_differential_diagnosis": False,
        "approved_icd10": False,
    }
    defaults.update(overrides)
    return DoctorReviewSummaryDTO(**defaults)  # type: ignore[arg-type]


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
        "encounter_datetime": datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
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
        "chief_complaint": None,
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
        "prescription_date": datetime(2026, 1, 1, tzinfo=UTC).date(),
        "status": PrescriptionStatus.FINAL,
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
        "ordered_at": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        "priority": Priority.ROUTINE,
        "status": LabOrderStatus.ORDERED,
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
        "reported_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "status": LabResultStatus.FINAL,
        "laboratory_name": None,
        "comments": None,
        "items": [],
    }
    defaults.update(overrides)
    return LabResultSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_differential_diagnosis_summary(**overrides: object) -> DifferentialDiagnosisSummaryDTO:
    defaults: dict[str, object] = {
        "differential_diagnosis_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "diagnosis_name": "Community-acquired pneumonia",
        "diagnosis_source": DiagnosisSource.AI,
        "ranking": 1,
        "review_status": DiagnosisReviewStatus.APPROVED,
        "excluded": False,
        "clinical_reasoning_id": None,
        "likelihood_score": None,
        "supporting_evidence": None,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_icd10_coding_summary(**overrides: object) -> ICD10CodingSummaryDTO:
    defaults: dict[str, object] = {
        "icd10_coding_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "icd10_code": "J18.9",
        "diagnosis_title": "Pneumonia, unspecified organism",
        "coding_source": CodingSource.AI,
        "primary_code": False,
        "review_status": ICD10ReviewStatus.APPROVED,
        "differential_diagnosis_id": None,
        "coding_notes": None,
    }
    defaults.update(overrides)
    return ICD10CodingSummaryDTO(**defaults)  # type: ignore[arg-type]
