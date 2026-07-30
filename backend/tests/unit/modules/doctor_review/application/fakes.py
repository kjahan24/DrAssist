"""In-memory test doubles for the Doctor Review module's repository, Unit
of Work, and the eight peer modules' public ports the use cases and
`DoctorReviewConsistencyService` depend on — each implements the exact
same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.

Every peer-module fake here is backed by a settable "which clinical
notes/lab orders have a record" collection, since
`DoctorReviewConsistencyService` only ever checks existence/non-emptiness
— it never reads the summary DTOs' other fields.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.public.dto import ClinicalReasoningSummaryDTO
from app.modules.clinical_reasoning.public.interfaces import ClinicalReasoningQueryPort
from app.modules.differential_diagnosis.public.dto import DifferentialDiagnosisSummaryDTO
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository
from app.modules.icd10_coding.public.dto import ICD10CodingSummaryDTO
from app.modules.icd10_coding.public.interfaces import ICD10CodingQueryPort
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.public.dto import LabOrderSummaryDTO
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.public.dto import LabResultSummaryDTO
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeDoctorReviewRepository(DoctorReviewRepository):
    def __init__(self) -> None:
        self._reviews: dict[UUID, DoctorReview] = {}

    async def get_by_id(self, doctor_review_id: UUID) -> DoctorReview | None:
        return self._reviews.get(doctor_review_id)

    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> DoctorReview | None:
        for review in self._reviews.values():
            if review.clinical_note_id == clinical_note_id:
                return review
        return None

    async def list_by_patient(self, patient_id: UUID) -> list[DoctorReview]:
        matches = [r for r in self._reviews.values() if r.patient_id == patient_id]
        return sorted(matches, key=lambda r: r.created_at)

    async def add(self, review: DoctorReview) -> None:
        self._reviews[review.id] = review


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


class FakeClinicalNoteQueryPort(ClinicalNoteQueryPort):
    """Backed by a settable map of "existing" clinical note id -> summary.
    `CreateDoctorReview` calls `get_clinical_note_summary` to check
    existence and derive identity fields."""

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
    def __init__(self, *, clinical_notes_with_soap_note: set[UUID] | None = None) -> None:
        self.clinical_notes_with_soap_note = clinical_notes_with_soap_note or set()

    async def soap_note_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.clinical_notes_with_soap_note

    async def get_soap_note_summary(self, clinical_note_id: UUID) -> SOAPNoteSummaryDTO | None:
        return None


class FakePrescriptionQueryPort(PrescriptionQueryPort):
    def __init__(self, *, clinical_notes_with_prescription: set[UUID] | None = None) -> None:
        self.clinical_notes_with_prescription = clinical_notes_with_prescription or set()

    async def prescription_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.clinical_notes_with_prescription

    async def get_prescription_summary(
        self, clinical_note_id: UUID
    ) -> PrescriptionSummaryDTO | None:
        return None

    async def list_prescriptions_for_patient(
        self, patient_id: UUID
    ) -> list[PrescriptionSummaryDTO]:
        return []


class FakeLabOrderQueryPort(LabOrderQueryPort):
    def __init__(
        self, *, lab_orders_by_clinical_note: dict[UUID, list[LabOrderSummaryDTO]] | None = None
    ) -> None:
        self.lab_orders_by_clinical_note = lab_orders_by_clinical_note or {}

    async def lab_order_exists(self, lab_order_id: UUID) -> bool:
        return False

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return False

    async def get_lab_order_summary(self, lab_order_id: UUID) -> LabOrderSummaryDTO | None:
        return None

    async def list_lab_orders_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[LabOrderSummaryDTO]:
        return self.lab_orders_by_clinical_note.get(clinical_note_id, [])

    async def list_lab_orders_for_patient(self, patient_id: UUID) -> list[LabOrderSummaryDTO]:
        return []


class FakeLabResultQueryPort(LabResultQueryPort):
    def __init__(self, *, lab_orders_with_result: set[UUID] | None = None) -> None:
        self.lab_orders_with_result = lab_orders_with_result or set()

    async def lab_result_exists_for_lab_order(self, lab_order_id: UUID) -> bool:
        return lab_order_id in self.lab_orders_with_result

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return False

    async def get_lab_result_summary(self, lab_order_id: UUID) -> LabResultSummaryDTO | None:
        return None

    async def list_lab_results_for_patient(self, patient_id: UUID) -> list[LabResultSummaryDTO]:
        return []


class FakeClinicalReasoningQueryPort(ClinicalReasoningQueryPort):
    def __init__(
        self,
        *,
        reasoning_by_clinical_note: dict[UUID, list[ClinicalReasoningSummaryDTO]] | None = None,
    ) -> None:
        self.reasoning_by_clinical_note = reasoning_by_clinical_note or {}

    async def clinical_reasoning_exists(self, clinical_reasoning_id: UUID) -> bool:
        return False

    async def is_editable(self, clinical_reasoning_id: UUID) -> bool:
        return False

    async def get_clinical_reasoning_summary(
        self, clinical_reasoning_id: UUID
    ) -> ClinicalReasoningSummaryDTO | None:
        return None

    async def list_clinical_reasoning_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
        return self.reasoning_by_clinical_note.get(clinical_note_id, [])

    async def list_clinical_reasoning_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
        return []


class FakeDifferentialDiagnosisQueryPort(DifferentialDiagnosisQueryPort):
    def __init__(
        self,
        *,
        diagnoses_by_clinical_note: dict[UUID, list[DifferentialDiagnosisSummaryDTO]] | None = None,
    ) -> None:
        self.diagnoses_by_clinical_note = diagnoses_by_clinical_note or {}

    async def differential_diagnosis_exists(self, differential_diagnosis_id: UUID) -> bool:
        return False

    async def is_editable(self, differential_diagnosis_id: UUID) -> bool:
        return False

    async def get_differential_diagnosis_summary(
        self, differential_diagnosis_id: UUID
    ) -> DifferentialDiagnosisSummaryDTO | None:
        return None

    async def list_differential_diagnoses_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        return self.diagnoses_by_clinical_note.get(clinical_note_id, [])

    async def list_differential_diagnoses_for_patient(
        self, patient_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]:
        return []


class FakeICD10CodingQueryPort(ICD10CodingQueryPort):
    def __init__(
        self, *, codings_by_clinical_note: dict[UUID, list[ICD10CodingSummaryDTO]] | None = None
    ) -> None:
        self.codings_by_clinical_note = codings_by_clinical_note or {}

    async def icd10_coding_exists(self, icd10_coding_id: UUID) -> bool:
        return False

    async def is_editable(self, icd10_coding_id: UUID) -> bool:
        return False

    async def get_icd10_coding_summary(self, icd10_coding_id: UUID) -> ICD10CodingSummaryDTO | None:
        return None

    async def get_primary_icd10_coding_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> ICD10CodingSummaryDTO | None:
        return None

    async def list_icd10_codings_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ICD10CodingSummaryDTO]:
        return self.codings_by_clinical_note.get(clinical_note_id, [])

    async def list_icd10_codings_for_patient(self, patient_id: UUID) -> list[ICD10CodingSummaryDTO]:
        return []


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
    }
    defaults.update(overrides)
    return ClinicalNoteSummaryDTO(**defaults)  # type: ignore[arg-type]


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
