"""In-memory test doubles for the Clinical Notes module's repository,
Unit of Work, and the Visit/Doctor modules' cross-module ports
`CreateClinicalNote` depends on — each implements the exact same
interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus
from app.modules.clinical_notes.domain.repositories import ClinicalNoteRepository
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.public.dto import DoctorSummaryDTO
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeClinicalNoteRepository(ClinicalNoteRepository):
    def __init__(self) -> None:
        self._notes: dict[UUID, ClinicalNote] = {}

    async def get_by_id(self, clinical_note_id: UUID) -> ClinicalNote | None:
        return self._notes.get(clinical_note_id)

    async def get_by_note_number(self, note_number: str) -> ClinicalNote | None:
        for note in self._notes.values():
            if note.note_number == note_number.strip():
                return note
        return None

    async def list_by_visit(self, visit_id: UUID) -> list[ClinicalNote]:
        matches = [n for n in self._notes.values() if n.visit_id == visit_id]
        return sorted(matches, key=lambda n: n.created_at)

    async def list_by_patient(self, patient_id: UUID) -> list[ClinicalNote]:
        matches = [n for n in self._notes.values() if n.patient_id == patient_id]
        return sorted(matches, key=lambda n: n.created_at)

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[ClinicalNoteStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        encounter_from: datetime | None = None,
        encounter_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_datetime",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[ClinicalNote], int]:
        matches = [n for n in self._notes.values() if n.organization_id == organization_id]
        if statuses:
            matches = [n for n in matches if n.status in statuses]
        if patient_id is not None:
            matches = [n for n in matches if n.patient_id == patient_id]
        if doctor_id is not None:
            matches = [n for n in matches if n.doctor_id == doctor_id]
        if visit_id is not None:
            matches = [n for n in matches if n.visit_id == visit_id]
        if encounter_from is not None:
            matches = [n for n in matches if n.encounter_datetime >= encounter_from]
        if encounter_to is not None:
            matches = [n for n in matches if n.encounter_datetime <= encounter_to]
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

            def _matches_query(n: ClinicalNote) -> bool:
                fields = (
                    n.note_number,
                    n.chief_complaint_summary,
                    n.history_summary,
                    n.examination_summary,
                    n.assessment_summary,
                    n.plan_summary,
                )
                return any(f is not None and term in f.lower() for f in fields)

            matches = [n for n in matches if _matches_query(n)]
        matches.sort(key=lambda n: getattr(n, sort_by, None) or "", reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, clinical_note: ClinicalNote) -> None:
        self._notes[clinical_note.id] = clinical_note


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


class FakeVisitQueryPort(VisitQueryPort):
    """Backed by a settable map of "existing" visit id -> (organization
    id, patient id) — `CreateClinicalNote` calls `get_visit_summary` to
    check existence, derive `organization_id`, and confirm the note's
    `patient_id` matches the visit's own patient."""

    def __init__(self, *, existing_visits: dict[UUID, tuple[UUID, UUID]] | None = None) -> None:
        self.existing_visits = existing_visits or {}

    async def visit_exists(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def is_active(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        entry = self.existing_visits.get(visit_id)
        if entry is None:
            return None
        organization_id, patient_id = entry
        return VisitSummaryDTO(
            visit_id=visit_id,
            organization_id=organization_id,
            patient_id=patient_id,
            doctor_id=uuid4(),
            visit_number="V-0001",
            visit_status=VisitStatus.SCHEDULED,
        )


class FakeDoctorQueryPort(DoctorQueryPort):
    """Backed by a settable map of "existing" doctor id -> organization
    id — `CreateClinicalNote` calls `get_doctor_summary` both to check
    existence and to confirm the doctor belongs to the same organization
    as the visit."""

    def __init__(self, *, existing_doctors: dict[UUID, UUID] | None = None) -> None:
        self.existing_doctors = existing_doctors or {}

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def is_active(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        organization_id = self.existing_doctors.get(doctor_id)
        if organization_id is None:
            return None
        return DoctorSummaryDTO(
            doctor_id=doctor_id,
            organization_id=organization_id,
            user_id=uuid4(),
            employee_id="EMP-001",
            joining_date=date(2020, 1, 1),
            status=DoctorStatus.ACTIVE,
        )
