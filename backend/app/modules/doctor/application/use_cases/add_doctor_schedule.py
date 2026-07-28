"""`AddDoctorSchedule` — a schedule entry always belongs to an existing
doctor, and must not overlap any existing entry for that doctor on the
same day of week (a doctor may have several entries per day — e.g. split
morning/evening shifts — so long as none overlap)."""

from app.modules.doctor.application.dto import AddDoctorScheduleInput, AddDoctorScheduleOutput
from app.modules.doctor.domain.entities import DoctorSchedule
from app.modules.doctor.domain.exceptions import DoctorNotFoundError, ScheduleOverlapError
from app.modules.doctor.domain.repositories import DoctorRepository, DoctorScheduleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddDoctorSchedule(UseCase[AddDoctorScheduleInput, AddDoctorScheduleOutput]):
    def __init__(
        self,
        *,
        doctor_schedule_repository: DoctorScheduleRepository,
        doctor_repository: DoctorRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._schedules = doctor_schedule_repository
        self._doctors = doctor_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AddDoctorScheduleInput) -> AddDoctorScheduleOutput:
        doctor = await self._doctors.get_by_id(input_dto.doctor_id)
        if doctor is None:
            raise DoctorNotFoundError(input_dto.doctor_id)

        schedule = DoctorSchedule.create(
            doctor_id=doctor.id,
            day_of_week=input_dto.day_of_week,
            start_time=input_dto.start_time,
            end_time=input_dto.end_time,
            break_start=input_dto.break_start,
            break_end=input_dto.break_end,
            is_available=input_dto.is_available,
        )

        existing_entries = await self._schedules.list_by_doctor_and_day(
            doctor.id, input_dto.day_of_week
        )
        if any(schedule.overlaps_with(entry) for entry in existing_entries):
            raise ScheduleOverlapError(doctor.id, input_dto.day_of_week)

        await self._schedules.add(schedule)
        self._uow.collect_events(schedule.pull_events())
        await self._uow.commit()

        return AddDoctorScheduleOutput(
            schedule_id=schedule.id,
            doctor_id=schedule.doctor_id,
            day_of_week=schedule.day_of_week,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
        )
