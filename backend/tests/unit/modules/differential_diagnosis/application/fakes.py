"""In-memory test doubles for the Differential Diagnosis module's
repository, Unit of Work, and the Clinical Notes/Clinical Reasoning
modules' public ports the use cases depend on — each implements the
exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from datetime import datetime
from uuid import UUID, uuid4

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.domain.enums import ReasoningSource
from app.modules.clinical_reasoning.domain.enums import ReviewStatus as ReasoningReviewStatus
from app.modules.clinical_reasoning.public.dto import ClinicalReasoningSummaryDTO
from app.modules.clinical_reasoning.public.interfaces import ClinicalReasoningQueryPort
from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeDifferentialDiagnosisRepository(DifferentialDiagnosisRepository):
    def __init__(self) -> None:
        self._diagnoses: dict[UUID, DifferentialDiagnosis] = {}

    async def get_by_id(self, differential_diagnosis_id: UUID) -> DifferentialDiagnosis | None:
        return self._diagnoses.get(differential_diagnosis_id)

    async def get_by_clinical_note_and_ranking(
        self, *, clinical_note_id: UUID, ranking: int
    ) -> DifferentialDiagnosis | None:
        for diagnosis in self._diagnoses.values():
            if diagnosis.clinical_note_id == clinical_note_id and diagnosis.ranking == ranking:
                return diagnosis
        return None

    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[DifferentialDiagnosis]:
        matches = [d for d in self._diagnoses.values() if d.clinical_note_id == clinical_note_id]
        return sorted(matches, key=lambda d: d.ranking)

    async def list_by_patient(self, patient_id: UUID) -> list[DifferentialDiagnosis]:
        matches = [d for d in self._diagnoses.values() if d.patient_id == patient_id]
        return sorted(matches, key=lambda d: d.created_at)

    async def add(self, diagnosis: DifferentialDiagnosis) -> None:
        self._diagnoses[diagnosis.id] = diagnosis


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
    `CreateDifferentialDiagnosis` calls `get_clinical_note_summary` to
    check existence and derive identity fields."""

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


class FakeClinicalReasoningQueryPort(ClinicalReasoningQueryPort):
    """Backed by a settable map of "existing" clinical reasoning id ->
    summary. `CreateDifferentialDiagnosis` calls
    `get_clinical_reasoning_summary` to check existence and validate the
    "same Clinical Note" cross-consistency rule."""

    def __init__(
        self, *, existing_records: dict[UUID, ClinicalReasoningSummaryDTO] | None = None
    ) -> None:
        self.existing_records = existing_records or {}

    async def clinical_reasoning_exists(self, clinical_reasoning_id: UUID) -> bool:
        return clinical_reasoning_id in self.existing_records

    async def is_editable(self, clinical_reasoning_id: UUID) -> bool:
        return clinical_reasoning_id in self.existing_records

    async def get_clinical_reasoning_summary(
        self, clinical_reasoning_id: UUID
    ) -> ClinicalReasoningSummaryDTO | None:
        return self.existing_records.get(clinical_reasoning_id)

    async def list_clinical_reasoning_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
        return [r for r in self.existing_records.values() if r.clinical_note_id == clinical_note_id]

    async def list_clinical_reasoning_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]:
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
        "encounter_datetime": datetime(2024, 1, 1, 9, 0),
        "ai_generated": False,
    }
    defaults.update(overrides)
    return ClinicalNoteSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_clinical_reasoning_summary(**overrides: object) -> ClinicalReasoningSummaryDTO:
    defaults: dict[str, object] = {
        "clinical_reasoning_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "reasoning_source": ReasoningSource.AI,
        "reasoning_text": "Elevated WBC suggests possible infection.",
        "ai_generated": True,
        "review_status": ReasoningReviewStatus.PENDING,
        "reviewed_by_doctor": False,
        "confidence_score": None,
    }
    defaults.update(overrides)
    return ClinicalReasoningSummaryDTO(**defaults)  # type: ignore[arg-type]
