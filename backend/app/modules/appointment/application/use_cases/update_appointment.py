"""`UpdateAppointment` — "Completed/NoShow appointments become
immutable", enforced solely by `Appointment.ensure_editable()` (this
aggregate's own status self-check, called internally by
`update_details()` — raises `AppointmentNotEditableError`). "Appointment
end_time must be later than start_time" is re-validated against the
*effective* post-update values inside `update_details()` itself.
"""

from app.modules.appointment.application.dto import (
    UpdateAppointmentInput,
    UpdateAppointmentOutput,
)
from app.modules.appointment.domain.exceptions import AppointmentNotFoundError
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateAppointment(UseCase[UpdateAppointmentInput, UpdateAppointmentOutput]):
    def __init__(
        self, *, appointment_repository: AppointmentRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._appointments = appointment_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateAppointmentInput) -> UpdateAppointmentOutput:
        appointment = await self._appointments.get_by_id(input_dto.appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError(input_dto.appointment_id)

        appointment.update_details(
            appointment_date=input_dto.appointment_date,
            start_time=input_dto.start_time,
            end_time=input_dto.end_time,
            appointment_type=input_dto.appointment_type,
            reason_for_visit=input_dto.reason_for_visit,
            notes=input_dto.notes,
        )
        await self._appointments.add(appointment)
        self._uow.collect_events(appointment.pull_events())
        await self._uow.commit()

        return UpdateAppointmentOutput(appointment_id=appointment.id)
