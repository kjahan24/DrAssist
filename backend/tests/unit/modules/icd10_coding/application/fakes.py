"""In-memory test doubles for the ICD-10 Coding module's repository, Unit
of Work, and the Clinical Notes/Differential Diagnosis modules' public
ports the use cases depend on — each implements the exact same interface
its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID, uuid4

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource
from app.modules.differential_diagnosis.domain.enums import ReviewStatus as DiagnosisReviewStatus
from app.modules.differential_diagnosis.public.dto import DifferentialDiagnosisSummaryDTO
from app.modules.differential_diagnosis.public.interfaces import DifferentialDiagnosisQueryPort
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeICD10CodingRepository(ICD10CodingRepository):
    def __init__(self) -> None:
        self._codings: dict[UUID, ICD10Coding] = {}

    async def get_by_id(self, icd10_coding_id: UUID) -> ICD10Coding | None:
        return self._codings.get(icd10_coding_id)

    async def get_primary_for_clinical_note(self, clinical_note_id: UUID) -> ICD10Coding | None:
        for coding in self._codings.values():
            if coding.clinical_note_id == clinical_note_id and coding.primary_code:
                return coding
        return None

    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[ICD10Coding]:
        matches = [c for c in self._codings.values() if c.clinical_note_id == clinical_note_id]
        return sorted(matches, key=lambda c: c.created_at)

    async def list_by_patient(self, patient_id: UUID) -> list[ICD10Coding]:
        matches = [c for c in self._codings.values() if c.patient_id == patient_id]
        return sorted(matches, key=lambda c: c.created_at)

    async def add(self, coding: ICD10Coding) -> None:
        self._codings[coding.id] = coding


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
    `CreateICD10Coding` calls `get_clinical_note_summary` to check
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


class FakeDifferentialDiagnosisQueryPort(DifferentialDiagnosisQueryPort):
    """Backed by a settable map of "existing" differential diagnosis id ->
    summary. `CreateICD10Coding` calls `get_differential_diagnosis_summary`
    to check existence and validate the "same Clinical Note" cross-
    consistency rule."""

    def __init__(
        self, *, existing_records: dict[UUID, DifferentialDiagnosisSummaryDTO] | None = None
    ) -> None:
        self.existing_records = existing_records or {}

    async def differential_diagnosis_exists(self, differential_diagnosis_id: UUID) -> bool:
        return differential_diagnosis_id in self.existing_records

    async def is_editable(self, differential_diagnosis_id: UUID) -> bool:
        return differential_diagnosis_id in self.existing_records

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
        return [r for r in self.existing_records.values() if r.patient_id == patient_id]


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
        "review_status": DiagnosisReviewStatus.PENDING,
        "excluded": False,
        "clinical_reasoning_id": None,
        "likelihood_score": None,
        "supporting_evidence": None,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisSummaryDTO(**defaults)  # type: ignore[arg-type]
