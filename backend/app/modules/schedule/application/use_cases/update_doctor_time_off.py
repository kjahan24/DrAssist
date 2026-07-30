"""`UpdateDoctorTimeOff` — re-checks "no overlap with siblings" against
the *effective* post-update datetime range whenever `start_datetime`/
`end_datetime` changes, the same in-memory-mutate-then-check technique
`app.modules.schedule.application.use_cases.update_doctor_schedule
.UpdateDoctorSchedule` uses for its own overlap rule.
"""

from app.modules.schedule.application.dto import (
    UpdateDoctorTimeOffInput,
    UpdateDoctorTimeOffOutput,
)
from app.modules.schedule.domain.exceptions import (
    DoctorTimeOffNotFoundError,
    DoctorTimeOffOverlapError,
)
from app.modules.schedule.domain.repositories import DoctorTimeOffRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateDoctorTimeOff(UseCase[UpdateDoctorTimeOffInput, UpdateDoctorTimeOffOutput]):
    def __init__(
        self, *, doctor_time_off_repository: DoctorTimeOffRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._time_off = doctor_time_off_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateDoctorTimeOffInput) -> UpdateDoctorTimeOffOutput:
        time_off = await self._time_off.get_by_id(input_dto.time_off_id)
        if time_off is None:
            raise DoctorTimeOffNotFoundError(input_dto.time_off_id)

        range_changed = input_dto.start_datetime is not None or input_dto.end_datetime is not None
        siblings = await self._time_off.list_by_doctor(time_off.doctor_id) if range_changed else []

        time_off.update_details(
            start_datetime=input_dto.start_datetime,
            end_datetime=input_dto.end_datetime,
            reason=input_dto.reason,
        )

        other_siblings = (sibling for sibling in siblings if sibling.id != time_off.id)
        if any(time_off.overlaps_with(sibling) for sibling in other_siblings):
            raise DoctorTimeOffOverlapError(time_off.doctor_id)

        await self._time_off.add(time_off)
        self._uow.collect_events(time_off.pull_events())
        await self._uow.commit()

        return UpdateDoctorTimeOffOutput(time_off_id=time_off.id)
