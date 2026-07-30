"""The Schedule/Availability module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.schedule.domain`, `.application` (beyond
this package), or `.infrastructure` from outside this module — this
file, `dto.py`, and `enums.py` are the entire allowed surface today.
This port is the contract every future scheduling-aware module (Calendar,
Appointment Booking, Google Calendar, Outlook Calendar, Holiday
Management, Recurring Availability, Resource Scheduling, Notification
Module) is expected to depend on to read a doctor's recurring weekly
availability and time-off periods — the same shape
`app.modules.appointment.public.interfaces.AppointmentQueryPort` already
establishes for its own module. One port covers both `DoctorSchedule`
and `DoctorTimeOff`: they are two peer aggregates of the same module,
presented as one cohesive surface rather than two competing ports —
computing "is this doctor actually free at time X" (active schedule for
that weekday/time window, minus any overlapping time-off) is left
entirely to that future consumer; this module deliberately does not
perform that computation itself (that is Appointment Booking's job, out
of scope here).
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.schedule.public.dto import DoctorScheduleSummaryDTO, DoctorTimeOffSummaryDTO
from app.modules.schedule.public.enums import Weekday


class ScheduleQueryPort(ABC):
    @abstractmethod
    async def doctor_schedule_exists(self, schedule_id: UUID) -> bool: ...

    @abstractmethod
    async def get_doctor_schedule_summary(
        self, schedule_id: UUID
    ) -> DoctorScheduleSummaryDTO | None: ...

    @abstractmethod
    async def list_doctor_schedules(self, doctor_id: UUID) -> list[DoctorScheduleSummaryDTO]: ...

    @abstractmethod
    async def list_active_doctor_schedules_for_weekday(
        self, doctor_id: UUID, weekday: Weekday
    ) -> list[DoctorScheduleSummaryDTO]: ...

    @abstractmethod
    async def doctor_time_off_exists(self, time_off_id: UUID) -> bool: ...

    @abstractmethod
    async def get_doctor_time_off_summary(
        self, time_off_id: UUID
    ) -> DoctorTimeOffSummaryDTO | None: ...

    @abstractmethod
    async def list_doctor_time_off(self, doctor_id: UUID) -> list[DoctorTimeOffSummaryDTO]: ...
