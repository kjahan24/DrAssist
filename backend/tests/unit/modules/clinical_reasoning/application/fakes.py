"""In-memory test doubles for the Clinical Reasoning module's repository,
Unit of Work, and the Clinical Notes module's public port the use cases
depend on — each implements the exact same interface its real
counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID, uuid4

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeClinicalReasoningRepository(ClinicalReasoningRepository):
    def __init__(self) -> None:
        self._records: dict[UUID, ClinicalReasoning] = {}

    async def get_by_id(self, clinical_reasoning_id: UUID) -> ClinicalReasoning | None:
        return self._records.get(clinical_reasoning_id)

    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[ClinicalReasoning]:
        matches = [r for r in self._records.values() if r.clinical_note_id == clinical_note_id]
        return sorted(matches, key=lambda r: r.created_at)

    async def list_by_patient(self, patient_id: UUID) -> list[ClinicalReasoning]:
        matches = [r for r in self._records.values() if r.patient_id == patient_id]
        return sorted(matches, key=lambda r: r.created_at)

    async def add(self, reasoning: ClinicalReasoning) -> None:
        self._records[reasoning.id] = reasoning


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
    `CreateClinicalReasoning` calls `get_clinical_note_summary` to check
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
