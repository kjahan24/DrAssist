"""Read-only queries against `DoctorTimeOff`.

Backs (together with `DoctorScheduleQueryService`) the module's public
`ScheduleQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance.
"""

from uuid import UUID

from app.modules.schedule.application.dto import DoctorTimeOffSummaryDTO
from app.modules.schedule.domain.entities import DoctorTimeOff
from app.modules.schedule.domain.repositories import DoctorTimeOffRepository


class DoctorTimeOffQueryService:
    def __init__(self, *, doctor_time_off_repository: DoctorTimeOffRepository) -> None:
        self._time_off = doctor_time_off_repository

    async def doctor_time_off_exists(self, time_off_id: UUID) -> bool:
        return await self._time_off.get_by_id(time_off_id) is not None

    async def get_doctor_time_off_summary(
        self, time_off_id: UUID
    ) -> DoctorTimeOffSummaryDTO | None:
        time_off = await self._time_off.get_by_id(time_off_id)
        return _to_summary(time_off) if time_off is not None else None

    async def list_doctor_time_off(self, doctor_id: UUID) -> list[DoctorTimeOffSummaryDTO]:
        time_off_periods = await self._time_off.list_by_doctor(doctor_id)
        return [_to_summary(time_off) for time_off in time_off_periods]


def _to_summary(time_off: DoctorTimeOff) -> DoctorTimeOffSummaryDTO:
    return DoctorTimeOffSummaryDTO(
        time_off_id=time_off.id,
        organization_id=time_off.organization_id,
        doctor_id=time_off.doctor_id,
        start_datetime=time_off.start_datetime,
        end_datetime=time_off.end_datetime,
        reason=time_off.reason,
    )
