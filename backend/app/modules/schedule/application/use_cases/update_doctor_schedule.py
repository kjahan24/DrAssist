"""`UpdateDoctorSchedule` — reschedules an existing entry's time range
and/or slot duration. Re-checks "no overlap with siblings" against the
*effective* time range whenever `start_time`/`end_time` changes, the same
re-validation-on-update precedent
`app.modules.appointment.application.use_cases.update_appointment
.UpdateAppointment` already establishes for its own "end_time must be
later than start_time" rule — comparing only against *active* siblings,
excluding this schedule's own row, and skipped entirely while this
schedule itself is inactive ("Inactive schedules are ignored").
"""

from app.modules.schedule.application.dto import (
    UpdateDoctorScheduleInput,
    UpdateDoctorScheduleOutput,
)
from app.modules.schedule.domain.exceptions import (
    DoctorScheduleNotFoundError,
    DoctorScheduleOverlapError,
)
from app.modules.schedule.domain.repositories import DoctorScheduleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateDoctorSchedule(UseCase[UpdateDoctorScheduleInput, UpdateDoctorScheduleOutput]):
    def __init__(
        self, *, doctor_schedule_repository: DoctorScheduleRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._schedules = doctor_schedule_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateDoctorScheduleInput) -> UpdateDoctorScheduleOutput:
        schedule = await self._schedules.get_by_id(input_dto.schedule_id)
        if schedule is None:
            raise DoctorScheduleNotFoundError(input_dto.schedule_id)

        time_range_changed = input_dto.start_time is not None or input_dto.end_time is not None
        siblings = (
            await self._schedules.list_active_by_doctor_and_weekday(
                schedule.doctor_id, schedule.weekday
            )
            if schedule.is_active and time_range_changed
            else []
        )

        # Mutate in-memory first so `overlaps_with()` compares the
        # *effective* post-update range — nothing is persisted until
        # `add()`/`commit()` below, so raising here after mutating is
        # still safe (no partial write reaches the database).
        schedule.update_details(
            start_time=input_dto.start_time,
            end_time=input_dto.end_time,
            slot_duration_minutes=input_dto.slot_duration_minutes,
        )

        other_siblings = (sibling for sibling in siblings if sibling.id != schedule.id)
        if any(schedule.overlaps_with(sibling) for sibling in other_siblings):
            raise DoctorScheduleOverlapError(schedule.doctor_id, schedule.weekday.value)

        await self._schedules.add(schedule)
        self._uow.collect_events(schedule.pull_events())
        await self._uow.commit()

        return UpdateDoctorScheduleOutput(schedule_id=schedule.id)
