"""`ConfirmAppointment` (Scheduled -> Confirmed)."""

from app.modules.appointment.application.dto import (
    AppointmentStatusOutput,
    ConfirmAppointmentInput,
)
from app.modules.appointment.domain.exceptions import AppointmentNotFoundError
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ConfirmAppointment(UseCase[ConfirmAppointmentInput, AppointmentStatusOutput]):
    def __init__(
        self, *, appointment_repository: AppointmentRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._appointments = appointment_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: ConfirmAppointmentInput) -> AppointmentStatusOutput:
        appointment = await self._appointments.get_by_id(input_dto.appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError(input_dto.appointment_id)

        appointment.confirm()
        await self._appointments.add(appointment)
        self._uow.collect_events(appointment.pull_events())
        await self._uow.commit()

        return AppointmentStatusOutput(appointment_id=appointment.id, status=appointment.status)
