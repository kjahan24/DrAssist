"""`CreateAppointment` — resolves `organization_id` from the linked
`Patient` and validates it against the linked `Doctor`'s own organization
via `AppointmentConsistencyService.resolve_and_validate_organization()`,
which is what makes "Patient and Doctor must belong to the same
Organization" a real runtime check — see `domain/entities.py` for why
`organization_id` is never independently trusted input.

"Appointment number must be globally unique" is checked via
`AppointmentRepository.get_by_appointment_number()` before construction —
the identical "query first, then construct" technique
`app.modules.icd10_coding.application.use_cases.create_icd10_coding
.CreateICD10Coding` already uses for its own duplicate-code prevention —
and is additionally backed by a database-level unique index (see
`infrastructure/models.py`).
"""

from app.modules.appointment.application.dto import (
    CreateAppointmentInput,
    CreateAppointmentOutput,
)
from app.modules.appointment.application.services.appointment_consistency_service import (
    AppointmentConsistencyService,
)
from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.exceptions import DuplicateAppointmentNumberError
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateAppointment(UseCase[CreateAppointmentInput, CreateAppointmentOutput]):
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

    async def execute(self, input_dto: CreateAppointmentInput) -> CreateAppointmentOutput:
        organization_id = await self._consistency.resolve_and_validate_organization(
            patient_id=input_dto.patient_id, doctor_id=input_dto.doctor_id
        )
        await self._consistency.validate_booked_by_user(
            booked_by_user_id=input_dto.booked_by_user_id, organization_id=organization_id
        )

        existing = await self._appointments.get_by_appointment_number(input_dto.appointment_number)
        if existing is not None:
            raise DuplicateAppointmentNumberError(input_dto.appointment_number)

        appointment = Appointment.create(
            organization_id=organization_id,
            patient_id=input_dto.patient_id,
            doctor_id=input_dto.doctor_id,
            appointment_number=input_dto.appointment_number,
            appointment_date=input_dto.appointment_date,
            start_time=input_dto.start_time,
            end_time=input_dto.end_time,
            appointment_type=input_dto.appointment_type,
            reason_for_visit=input_dto.reason_for_visit,
            notes=input_dto.notes,
            booked_by_user_id=input_dto.booked_by_user_id,
        )
        await self._appointments.add(appointment)
        self._uow.collect_events(appointment.pull_events())
        await self._uow.commit()

        return CreateAppointmentOutput(
            appointment_id=appointment.id,
            organization_id=appointment.organization_id,
            appointment_number=appointment.appointment_number,
            status=appointment.status,
        )
