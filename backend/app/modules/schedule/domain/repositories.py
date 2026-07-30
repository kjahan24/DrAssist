"""Repository interfaces for the `DoctorSchedule`/`DoctorTimeOff`
aggregates, expressed in domain vocabulary only (no session, no SQL).
Concrete implementations live in
`app.modules.schedule.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method on either interface: a repository returns the
actual aggregate object, the caller mutates it via its own methods, and
the Unit of Work's `commit()` persists the change through SQLAlchemy's
session-level change tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.schedule.domain.entities import DoctorSchedule, DoctorTimeOff
from app.modules.schedule.domain.enums import Weekday


class DoctorScheduleRepository(ABC):
    @abstractmethod
    async def get_by_id(self, schedule_id: UUID) -> DoctorSchedule | None: ...

    @abstractmethod
    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSchedule]: ...

    @abstractmethod
    async def list_active_by_doctor_and_weekday(
        self, doctor_id: UUID, weekday: Weekday
    ) -> list[DoctorSchedule]: ...

    @abstractmethod
    async def add(self, schedule: DoctorSchedule) -> None: ...


class DoctorTimeOffRepository(ABC):
    @abstractmethod
    async def get_by_id(self, time_off_id: UUID) -> DoctorTimeOff | None: ...

    @abstractmethod
    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorTimeOff]: ...

    @abstractmethod
    async def add(self, time_off: DoctorTimeOff) -> None: ...
