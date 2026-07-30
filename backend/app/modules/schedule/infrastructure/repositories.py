"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.icd10_coding.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schedule.domain.entities import DoctorSchedule, DoctorTimeOff
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.repositories import (
    DoctorScheduleRepository,
    DoctorTimeOffRepository,
)
from app.modules.schedule.infrastructure.mappers import (
    apply_doctor_schedule_to_model,
    apply_doctor_time_off_to_model,
    doctor_schedule_to_domain,
    doctor_time_off_to_domain,
)
from app.modules.schedule.infrastructure.models import DoctorScheduleModel, DoctorTimeOffModel


class SqlAlchemyDoctorScheduleRepository(DoctorScheduleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, schedule_id: UUID) -> DoctorSchedule | None:
        model = await self._session.get(DoctorScheduleModel, schedule_id)
        if model is None or model.deleted_at is not None:
            return None
        return doctor_schedule_to_domain(model)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorSchedule]:
        stmt = (
            select(DoctorScheduleModel)
            .where(
                DoctorScheduleModel.doctor_id == doctor_id,
                DoctorScheduleModel.deleted_at.is_(None),
            )
            .order_by(DoctorScheduleModel.weekday, DoctorScheduleModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_schedule_to_domain(model) for model in models]

    async def list_active_by_doctor_and_weekday(
        self, doctor_id: UUID, weekday: Weekday
    ) -> list[DoctorSchedule]:
        stmt = (
            select(DoctorScheduleModel)
            .where(
                DoctorScheduleModel.doctor_id == doctor_id,
                DoctorScheduleModel.weekday == weekday,
                DoctorScheduleModel.is_active.is_(True),
                DoctorScheduleModel.deleted_at.is_(None),
            )
            .order_by(DoctorScheduleModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_schedule_to_domain(model) for model in models]

    async def add(self, schedule: DoctorSchedule) -> None:
        model = await self._session.get(DoctorScheduleModel, schedule.id)
        if model is None:
            model = DoctorScheduleModel()
            self._session.add(model)
        apply_doctor_schedule_to_model(schedule, model)


class SqlAlchemyDoctorTimeOffRepository(DoctorTimeOffRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, time_off_id: UUID) -> DoctorTimeOff | None:
        model = await self._session.get(DoctorTimeOffModel, time_off_id)
        if model is None or model.deleted_at is not None:
            return None
        return doctor_time_off_to_domain(model)

    async def list_by_doctor(self, doctor_id: UUID) -> list[DoctorTimeOff]:
        stmt = (
            select(DoctorTimeOffModel)
            .where(
                DoctorTimeOffModel.doctor_id == doctor_id,
                DoctorTimeOffModel.deleted_at.is_(None),
            )
            .order_by(DoctorTimeOffModel.start_datetime)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_time_off_to_domain(model) for model in models]

    async def add(self, time_off: DoctorTimeOff) -> None:
        model = await self._session.get(DoctorTimeOffModel, time_off.id)
        if model is None:
            model = DoctorTimeOffModel()
            self._session.add(model)
        apply_doctor_time_off_to_model(time_off, model)
