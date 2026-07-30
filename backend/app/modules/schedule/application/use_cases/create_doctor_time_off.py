"""`CreateDoctorTimeOff` — resolves `organization_id` from the linked
`Doctor` the same way `CreateDoctorSchedule` does. "A doctor cannot have
overlapping time-off periods" is checked via
`DoctorTimeOffRepository.list_by_doctor()` before construction — the
identical "query first, then construct" technique
`CreateDoctorSchedule` uses for its own overlap rule.
"""

from app.modules.schedule.application.dto import (
    CreateDoctorTimeOffInput,
    CreateDoctorTimeOffOutput,
)
from app.modules.schedule.application.services.schedule_consistency_service import (
    ScheduleConsistencyService,
)
from app.modules.schedule.domain.entities import DoctorTimeOff
from app.modules.schedule.domain.exceptions import DoctorTimeOffOverlapError
from app.modules.schedule.domain.repositories import DoctorTimeOffRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateDoctorTimeOff(UseCase[CreateDoctorTimeOffInput, CreateDoctorTimeOffOutput]):
    def __init__(
        self,
        *,
        doctor_time_off_repository: DoctorTimeOffRepository,
        consistency_service: ScheduleConsistencyService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._time_off = doctor_time_off_repository
        self._consistency = consistency_service
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateDoctorTimeOffInput) -> CreateDoctorTimeOffOutput:
        organization_id = await self._consistency.resolve_organization_for_doctor(
            input_dto.doctor_id
        )

        time_off = DoctorTimeOff.create(
            organization_id=organization_id,
            doctor_id=input_dto.doctor_id,
            start_datetime=input_dto.start_datetime,
            end_datetime=input_dto.end_datetime,
            reason=input_dto.reason,
        )

        existing = await self._time_off.list_by_doctor(input_dto.doctor_id)
        if any(time_off.overlaps_with(entry) for entry in existing):
            raise DoctorTimeOffOverlapError(input_dto.doctor_id)

        await self._time_off.add(time_off)
        self._uow.collect_events(time_off.pull_events())
        await self._uow.commit()

        return CreateDoctorTimeOffOutput(
            time_off_id=time_off.id,
            organization_id=time_off.organization_id,
            doctor_id=time_off.doctor_id,
        )
