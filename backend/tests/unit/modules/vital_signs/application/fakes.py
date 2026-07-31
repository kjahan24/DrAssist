"""In-memory test doubles for the Vital Signs module's repository, Unit of
Work, and the Visit/Doctor modules' cross-module ports
`RecordVisitVitalSigns` depends on — each implements the exact same
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
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort
from app.modules.vital_signs.domain.entities import VisitVitalSigns
from app.modules.vital_signs.domain.repositories import VisitVitalSignsRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeVisitVitalSignsRepository(VisitVitalSignsRepository):
    def __init__(self) -> None:
        self._records: dict[UUID, VisitVitalSigns] = {}

    async def get_by_id(self, vital_signs_id: UUID) -> VisitVitalSigns | None:
        return self._records.get(vital_signs_id)

    async def get_by_visit_id(self, visit_id: UUID) -> VisitVitalSigns | None:
        for record in self._records.values():
            if record.visit_id == visit_id:
                return record
        return None

    async def add(self, vital_signs: VisitVitalSigns) -> None:
        self._records[vital_signs.id] = vital_signs


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
    id — `RecordVisitVitalSigns` calls `get_visit_summary` both to check
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
    id — `RecordVisitVitalSigns` calls `get_doctor_summary` both to check
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
