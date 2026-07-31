"""In-memory test doubles for the SOAP Notes module's repository, Unit of
Work, and the Clinical Notes module's public port `CreateSOAPNote`/
`UpdateSOAPNote` depend on — each implements the exact same interface its
real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.domain.repositories import SOAPNoteRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeSOAPNoteRepository(SOAPNoteRepository):
    def __init__(self) -> None:
        self._notes: dict[UUID, SOAPNote] = {}

    async def get_by_id(self, soap_note_id: UUID) -> SOAPNote | None:
        return self._notes.get(soap_note_id)

    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> SOAPNote | None:
        for note in self._notes.values():
            if note.clinical_note_id == clinical_note_id:
                return note
        return None

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[SOAPNote], int]:
        matches = [n for n in self._notes.values() if n.organization_id == organization_id]
        if patient_id is not None:
            matches = [n for n in matches if n.patient_id == patient_id]
        if doctor_id is not None:
            matches = [n for n in matches if n.doctor_id == doctor_id]
        if visit_id is not None:
            matches = [n for n in matches if n.visit_id == visit_id]
        if created_from is not None:
            matches = [n for n in matches if n.created_at >= created_from]
        if created_to is not None:
            matches = [n for n in matches if n.created_at <= created_to]
        if updated_from is not None:
            matches = [n for n in matches if n.updated_at >= updated_from]
        if updated_to is not None:
            matches = [n for n in matches if n.updated_at <= updated_to]
        if query:
            term = query.strip().lower()

            def _matches_query(n: SOAPNote) -> bool:
                fields = (
                    n.chief_complaint,
                    n.history_of_present_illness,
                    n.review_of_systems,
                    n.physical_examination,
                    n.assessment,
                    n.plan,
                )
                return any(f is not None and term in f.lower() for f in fields)

            matches = [n for n in matches if _matches_query(n)]
        matches.sort(key=lambda n: getattr(n, sort_by, None) or "", reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, soap_note: SOAPNote) -> None:
        self._notes[soap_note.id] = soap_note


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
    """Backed by a settable map of "existing" clinical note id -> summary,
    plus a separate `not_editable` set. `CreateSOAPNote`/`UpdateSOAPNote`
    call `get_clinical_note_summary` to check existence and derive
    identity fields, and `is_editable` to enforce the read-only rule."""

    def __init__(
        self,
        *,
        existing_notes: dict[UUID, ClinicalNoteSummaryDTO] | None = None,
        not_editable: set[UUID] | None = None,
    ) -> None:
        self.existing_notes = existing_notes or {}
        self.not_editable = not_editable or set()

    async def clinical_note_exists(self, clinical_note_id: UUID) -> bool:
        return clinical_note_id in self.existing_notes

    async def is_editable(self, clinical_note_id: UUID) -> bool:
        if clinical_note_id not in self.existing_notes:
            return False
        return clinical_note_id not in self.not_editable

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
        "encounter_datetime": datetime(2024, 1, 1, 9, 0),
        "ai_generated": False,
    }
    defaults.update(overrides)
    return ClinicalNoteSummaryDTO(**defaults)  # type: ignore[arg-type]
