"""In-memory test doubles for the Procedures module's repository, Unit of
Work, and the Visit/Doctor modules' cross-module ports
`RecordVisitProcedure` depends on — each implements the exact same
interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from datetime import date
from uuid import UUID, uuid4

from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.public.dto import DoctorSummaryDTO
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.procedures.domain.entities import VisitProcedure
from app.modules.procedures.domain.repositories import VisitProcedureRepository
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeVisitProcedureRepository(VisitProcedureRepository):
    def __init__(self) -> None:
        self._procedures: dict[UUID, VisitProcedure] = {}

    async def get_by_id(self, procedure_id: UUID) -> VisitProcedure | None:
        return self._procedures.get(procedure_id)

    async def get_by_visit_and_sequence(
        self, *, visit_id: UUID, sequence_number: int
    ) -> VisitProcedure | None:
        for procedure in self._procedures.values():
            if procedure.visit_id == visit_id and procedure.sequence_number == sequence_number:
                return procedure
        return None

    async def list_by_visit(self, visit_id: UUID) -> list[VisitProcedure]:
        matches = [p for p in self._procedures.values() if p.visit_id == visit_id]
        return sorted(matches, key=lambda p: p.sequence_number)

    async def add(self, procedure: VisitProcedure) -> None:
        self._procedures[procedure.id] = procedure


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
    """Backed by a settable map of "existing" visit id -> organization
    id — `RecordVisitProcedure` calls `get_visit_summary` both to check
    existence and to derive `organization_id`."""

    def __init__(self, *, existing_visits: dict[UUID, UUID] | None = None) -> None:
        self.existing_visits = existing_visits or {}

    async def visit_exists(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def is_active(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        organization_id = self.existing_visits.get(visit_id)
        if organization_id is None:
            return None
        return VisitSummaryDTO(
            visit_id=visit_id,
            organization_id=organization_id,
            patient_id=uuid4(),
            doctor_id=uuid4(),
            visit_number="V-0001",
            visit_status=VisitStatus.SCHEDULED,
        )


class FakeDoctorQueryPort(DoctorQueryPort):
    """Backed by a settable map of "existing" doctor id -> organization
    id — `RecordVisitProcedure` calls `get_doctor_summary` both to check
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
