"""Read-only queries against `DoctorSchedule`.

Backs (together with `DoctorTimeOffQueryService`) the module's public
`ScheduleQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; these internal services don't need a second one).

`list_active_doctor_schedules_for_weekday` exists specifically for future
Appointment Booking/Calendar consumers, which need "what hours is this
doctor bookable on Tuesdays" without re-deriving "ignore inactive
entries" themselves — "Inactive schedules are ignored" is applied here
too, not only at write time.
"""

from uuid import UUID

from app.modules.schedule.application.dto import DoctorScheduleSummaryDTO
from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.repositories import DoctorScheduleRepository


class DoctorScheduleQueryService:
    def __init__(self, *, doctor_schedule_repository: DoctorScheduleRepository) -> None:
        self._schedules = doctor_schedule_repository

    async def doctor_schedule_exists(self, schedule_id: UUID) -> bool:
        return await self._schedules.get_by_id(schedule_id) is not None

    async def get_doctor_schedule_summary(
        self, schedule_id: UUID
    ) -> DoctorScheduleSummaryDTO | None:
        schedule = await self._schedules.get_by_id(schedule_id)
        return _to_summary(schedule) if schedule is not None else None

    async def list_doctor_schedules(self, doctor_id: UUID) -> list[DoctorScheduleSummaryDTO]:
        schedules = await self._schedules.list_by_doctor(doctor_id)
        return [_to_summary(schedule) for schedule in schedules]

    async def list_active_doctor_schedules_for_weekday(
        self, doctor_id: UUID, weekday: Weekday
    ) -> list[DoctorScheduleSummaryDTO]:
        schedules = await self._schedules.list_active_by_doctor_and_weekday(doctor_id, weekday)
        return [_to_summary(schedule) for schedule in schedules]


def _to_summary(schedule: DoctorSchedule) -> DoctorScheduleSummaryDTO:
    return DoctorScheduleSummaryDTO(
        schedule_id=schedule.id,
        organization_id=schedule.organization_id,
        doctor_id=schedule.doctor_id,
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        slot_duration_minutes=schedule.slot_duration_minutes,
        is_active=schedule.is_active,
    )
