"""`CompleteAppointment` ((CheckedIn|InProgress) -> Completed) — "One
completed appointment may optionally create one Visit". When `visit_id`
is supplied, it is validated through `AppointmentConsistencyService
.validate_visit_for_completion()` (existence + organization/patient/
doctor consistency via `VisitQueryPort`) *before* `Appointment.complete()`
is called — this module never creates a `Visit` itself, it only records
a link to one that already exists.
"""

from app.modules.appointment.application.dto import (
    AppointmentStatusOutput,
    CompleteAppointmentInput,
)
from app.modules.appointment.application.services.appointment_consistency_service import (
    AppointmentConsistencyService,
)
from app.modules.appointment.domain.exceptions import AppointmentNotFoundError
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CompleteAppointment(UseCase[CompleteAppointmentInput, AppointmentStatusOutput]):
    def __init__(
        self,
        *,
        appointment_repository: AppointmentRepository,
        consistency_service: AppointmentConsistencyService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._appointments = appointment_repository
        self._consistency = consistency_service
        self._uow = unit_of_work

    async def execute(self, input_dto: CompleteAppointmentInput) -> AppointmentStatusOutput:
        appointment = await self._appointments.get_by_id(input_dto.appointment_id)
        if appointment is None:
            raise AppointmentNotFoundError(input_dto.appointment_id)

        await self._consistency.validate_visit_for_completion(
            visit_id=input_dto.visit_id,
            organization_id=appointment.organization_id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
        )

        appointment.complete(visit_id=input_dto.visit_id)
        await self._appointments.add(appointment)
        self._uow.collect_events(appointment.pull_events())
        await self._uow.commit()

        return AppointmentStatusOutput(appointment_id=appointment.id, status=appointment.status)
