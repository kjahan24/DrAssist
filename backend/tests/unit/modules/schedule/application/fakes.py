"""In-memory test doubles for the Schedule/Availability module's
repositories, Unit of Work, and the Doctor module's public port
`ScheduleConsistencyService` depends on — each implements the exact same
interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from datetime import date
from uuid import UUID, uuid4

from app.modules.doctor.application.dto import DoctorSummaryDTO
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.schedule.domain.entities import DoctorSchedule, DoctorTimeOff
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.repositories import (
    DoctorScheduleRepository,
    DoctorTimeOffRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeDoctorScheduleRepository(DoctorScheduleRepository):
    def __init__(self) -> None:
        self._schedules: dict[UUID, DoctorSchedule] = {}

    async def get_by_id(self, schedule_id: UUID) -> DoctorSchedule | None:
        return self._schedules.get(schedule_id)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSchedule]:
        matches = [s for s in self._schedules.values() if s.doctor_id == doctor_id]
        return sorted(matches, key=lambda s: (s.weekday, s.start_time))

    async def list_active_by_doctor_and_weekday(
        self, doctor_id: UUID, weekday: Weekday
    ) -> list[DoctorSchedule]:
        matches = [
            s
            for s in self._schedules.values()
            if s.doctor_id == doctor_id and s.weekday == weekday and s.is_active
        ]
        return sorted(matches, key=lambda s: s.start_time)

    async def add(self, schedule: DoctorSchedule) -> None:
        self._schedules[schedule.id] = schedule


class FakeDoctorTimeOffRepository(DoctorTimeOffRepository):
    def __init__(self) -> None:
        self._time_off: dict[UUID, DoctorTimeOff] = {}

    async def get_by_id(self, time_off_id: UUID) -> DoctorTimeOff | None:
        return self._time_off.get(time_off_id)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorTimeOff]:
        matches = [t for t in self._time_off.values() if t.doctor_id == doctor_id]
        return sorted(matches, key=lambda t: t.start_datetime)

    async def add(self, time_off: DoctorTimeOff) -> None:
        self._time_off[time_off.id] = time_off


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


class FakeDoctorQueryPort(DoctorQueryPort):
    def __init__(self, *, existing_doctors: dict[UUID, DoctorSummaryDTO] | None = None) -> None:
        self.existing_doctors = existing_doctors or {}

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def is_active(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        return self.existing_doctors.get(doctor_id)


def make_doctor_summary(**overrides: object) -> DoctorSummaryDTO:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "employee_id": "EMP-0001",
        "joining_date": date(2020, 1, 1),
        "status": DoctorStatus.ACTIVE,
    }
    defaults.update(overrides)
    return DoctorSummaryDTO(**defaults)  # type: ignore[arg-type]
