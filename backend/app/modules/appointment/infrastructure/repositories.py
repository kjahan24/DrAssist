"""Concrete SQLAlchemy repository implementation.

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

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.modules.appointment.infrastructure.mappers import (
    apply_appointment_to_model,
    appointment_to_domain,
)
from app.modules.appointment.infrastructure.models import AppointmentModel


class SqlAlchemyAppointmentRepository(AppointmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, appointment_id: UUID) -> Appointment | None:
        model = await self._session.get(AppointmentModel, appointment_id)
        if model is None or model.deleted_at is not None:
            return None
        return appointment_to_domain(model)

    async def get_by_appointment_number(self, appointment_number: str) -> Appointment | None:
        stmt = select(AppointmentModel).where(
            AppointmentModel.appointment_number == appointment_number,
            AppointmentModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return appointment_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[Appointment]:
        stmt = (
            select(AppointmentModel)
            .where(
                AppointmentModel.patient_id == patient_id,
                AppointmentModel.deleted_at.is_(None),
            )
            .order_by(AppointmentModel.appointment_date, AppointmentModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [appointment_to_domain(model) for model in models]

    async def list_by_doctor(self, doctor_id: UUID) -> list[Appointment]:
        stmt = (
            select(AppointmentModel)
            .where(
                AppointmentModel.doctor_id == doctor_id,
                AppointmentModel.deleted_at.is_(None),
            )
            .order_by(AppointmentModel.appointment_date, AppointmentModel.start_time)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [appointment_to_domain(model) for model in models]

    async def add(self, appointment: Appointment) -> None:
        model = await self._session.get(AppointmentModel, appointment.id)
        if model is None:
            model = AppointmentModel()
            self._session.add(model)
        apply_appointment_to_model(appointment, model)
