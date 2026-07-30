"""`CreateDoctorSchedule` — resolves `organization_id` from the linked
`Doctor` via `ScheduleConsistencyService.resolve_organization_for_doctor()`,
which is what makes "Doctor and Organization must match" true by
construction — see `domain/entities.py`.

"A doctor cannot have overlapping schedules on the same weekday" is
checked via `DoctorScheduleRepository.list_active_by_doctor_and_weekday()`
before construction (comparing against *active* siblings only —
"Inactive schedules are ignored") — the identical "query first, then
construct" technique, and the identical overlap-detection shape,
`app.modules.doctor.application.use_cases.add_doctor_schedule
.AddDoctorSchedule` already establishes for the pre-existing, differently
-shaped `doctor.DoctorSchedule` (see `domain/entities.py` for why this
module has its own, separate `DoctorSchedule`).
"""

from app.modules.schedule.application.dto import (
    CreateDoctorScheduleInput,
    CreateDoctorScheduleOutput,
)
from app.modules.schedule.application.services.schedule_consistency_service import (
    ScheduleConsistencyService,
)
from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.exceptions import DoctorScheduleOverlapError
from app.modules.schedule.domain.repositories import DoctorScheduleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateDoctorSchedule(UseCase[CreateDoctorScheduleInput, CreateDoctorScheduleOutput]):
    def __init__(
        self,
        *,
        doctor_schedule_repository: DoctorScheduleRepository,
        consistency_service: ScheduleConsistencyService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._schedules = doctor_schedule_repository
        self._consistency = consistency_service
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateDoctorScheduleInput) -> CreateDoctorScheduleOutput:
        organization_id = await self._consistency.resolve_organization_for_doctor(
            input_dto.doctor_id
        )

        schedule = DoctorSchedule.create(
            organization_id=organization_id,
            doctor_id=input_dto.doctor_id,
            weekday=input_dto.weekday,
            start_time=input_dto.start_time,
            end_time=input_dto.end_time,
            slot_duration_minutes=input_dto.slot_duration_minutes,
            is_active=input_dto.is_active,
        )

        if schedule.is_active:
            existing = await self._schedules.list_active_by_doctor_and_weekday(
                input_dto.doctor_id, input_dto.weekday
            )
            if any(schedule.overlaps_with(entry) for entry in existing):
                raise DoctorScheduleOverlapError(input_dto.doctor_id, input_dto.weekday.value)

        await self._schedules.add(schedule)
        self._uow.collect_events(schedule.pull_events())
        await self._uow.commit()

        return CreateDoctorScheduleOutput(
            schedule_id=schedule.id,
            organization_id=schedule.organization_id,
            doctor_id=schedule.doctor_id,
            weekday=schedule.weekday,
        )
