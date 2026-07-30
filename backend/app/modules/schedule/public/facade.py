"""`ScheduleFacade` — the one concrete implementation of
`ScheduleQueryPort`. Constructed per-request by
`app.modules.schedule.container.build_schedule_facade`, bound to that
request's `AsyncSession`. Delegates to `DoctorScheduleQueryService`/
`DoctorTimeOffQueryService` — this facade itself holds no logic beyond
that delegation.
"""

from uuid import UUID

from app.modules.schedule.application.services.doctor_schedule_query_service import (
    DoctorScheduleQueryService,
)
from app.modules.schedule.application.services.doctor_time_off_query_service import (
    DoctorTimeOffQueryService,
)
from app.modules.schedule.public.dto import DoctorScheduleSummaryDTO, DoctorTimeOffSummaryDTO
from app.modules.schedule.public.enums import Weekday
from app.modules.schedule.public.interfaces import ScheduleQueryPort


class ScheduleFacade(ScheduleQueryPort):
    def __init__(
        self,
        *,
        doctor_schedule_query_service: DoctorScheduleQueryService,
        doctor_time_off_query_service: DoctorTimeOffQueryService,
    ) -> None:
        self._schedules = doctor_schedule_query_service
        self._time_off = doctor_time_off_query_service

    async def doctor_schedule_exists(self, schedule_id: UUID) -> bool:
        return await self._schedules.doctor_schedule_exists(schedule_id)

    async def get_doctor_schedule_summary(
        self, schedule_id: UUID
    ) -> DoctorScheduleSummaryDTO | None:
        return await self._schedules.get_doctor_schedule_summary(schedule_id)

    async def list_doctor_schedules(self, doctor_id: UUID) -> list[DoctorScheduleSummaryDTO]:
        return await self._schedules.list_doctor_schedules(doctor_id)

    async def list_active_doctor_schedules_for_weekday(
        self, doctor_id: UUID, weekday: Weekday
    ) -> list[DoctorScheduleSummaryDTO]:
        return await self._schedules.list_active_doctor_schedules_for_weekday(doctor_id, weekday)

    async def doctor_time_off_exists(self, time_off_id: UUID) -> bool:
        return await self._time_off.doctor_time_off_exists(time_off_id)

    async def get_doctor_time_off_summary(
        self, time_off_id: UUID
    ) -> DoctorTimeOffSummaryDTO | None:
        return await self._time_off.get_doctor_time_off_summary(time_off_id)

    async def list_doctor_time_off(self, doctor_id: UUID) -> list[DoctorTimeOffSummaryDTO]:
        return await self._time_off.list_doctor_time_off(doctor_id)
