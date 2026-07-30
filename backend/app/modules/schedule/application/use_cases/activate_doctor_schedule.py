"""`ActivateDoctorSchedule` — re-enables a previously deactivated entry.
Re-checks "no overlap with active siblings" at the moment of activation:
"Inactive schedules are ignored" means overlap-checking only actually
matters between *active* entries, so re-entering the active set is
exactly the moment this schedule could newly conflict with a sibling
that was created (or itself activated) while this one was inactive.
"""

from app.modules.schedule.application.dto import (
    ActivateDoctorScheduleInput,
    DoctorScheduleActiveOutput,
)
from app.modules.schedule.domain.exceptions import (
    DoctorScheduleNotFoundError,
    DoctorScheduleOverlapError,
)
from app.modules.schedule.domain.repositories import DoctorScheduleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ActivateDoctorSchedule(UseCase[ActivateDoctorScheduleInput, DoctorScheduleActiveOutput]):
    def __init__(
        self, *, doctor_schedule_repository: DoctorScheduleRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._schedules = doctor_schedule_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: ActivateDoctorScheduleInput) -> DoctorScheduleActiveOutput:
        schedule = await self._schedules.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise DoctorScheduleNotFoundError(input_dto.schedule_id)

        if not schedule.is_active:
            siblings = await self._schedules.list_active_by_doctor_and_weekday(
                schedule.doctor_id, schedule.weekday
            )
            if any(schedule.overlaps_with(sibling) for sibling in siblings):
                raise DoctorScheduleOverlapError(schedule.doctor_id, schedule.weekday.value)

        schedule.activate()
        await self._schedules.add(schedule)
        self._uow.collect_events(schedule.pull_events())
        await self._uow.commit()

        return DoctorScheduleActiveOutput(schedule_id=schedule.id, is_active=schedule.is_active)
