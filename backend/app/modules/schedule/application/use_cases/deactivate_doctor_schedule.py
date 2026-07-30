"""`DeactivateDoctorSchedule` — "Inactive schedules are ignored". No
overlap re-check is needed: removing an entry from the active set can
never create a new overlap.
"""

from app.modules.schedule.application.dto import (
    DeactivateDoctorScheduleInput,
    DoctorScheduleActiveOutput,
)
from app.modules.schedule.domain.exceptions import DoctorScheduleNotFoundError
from app.modules.schedule.domain.repositories import DoctorScheduleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class DeactivateDoctorSchedule(UseCase[DeactivateDoctorScheduleInput, DoctorScheduleActiveOutput]):
    def __init__(
        self, *, doctor_schedule_repository: DoctorScheduleRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._schedules = doctor_schedule_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: DeactivateDoctorScheduleInput) -> DoctorScheduleActiveOutput:
        schedule = await self._schedules.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise DoctorScheduleNotFoundError(input_dto.schedule_id)

        schedule.deactivate()
        await self._schedules.add(schedule)
        self._uow.collect_events(schedule.pull_events())
        await self._uow.commit()

        return DoctorScheduleActiveOutput(schedule_id=schedule.id, is_active=schedule.is_active)
