"""`AddDoctorSpecialization` — a specialization always belongs to an
existing doctor. When added as primary, any previously-primary
specialization for the same doctor is unset first, so "at most one
primary specialization per doctor" holds without requiring the caller to
manage it."""

from app.modules.doctor.application.dto import (
    AddDoctorSpecializationInput,
    AddDoctorSpecializationOutput,
)
from app.modules.doctor.domain.entities import DoctorSpecialization
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.doctor.domain.repositories import DoctorRepository, DoctorSpecializationRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddDoctorSpecialization(UseCase[AddDoctorSpecializationInput, AddDoctorSpecializationOutput]):
    def __init__(
        self,
        *,
        doctor_specialization_repository: DoctorSpecializationRepository,
        doctor_repository: DoctorRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._specializations = doctor_specialization_repository
        self._doctors = doctor_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: AddDoctorSpecializationInput
    ) -> AddDoctorSpecializationOutput:
        doctor = await self._doctors.get_by_id(input_dto.doctor_id)
        if doctor is None:
            raise DoctorNotFoundError(input_dto.doctor_id)

        if input_dto.is_primary:
            await self._specializations.unset_primary_for_doctor(doctor.id)

        specialization = DoctorSpecialization.create(
            organization_id=doctor.organization_id,
            doctor_id=doctor.id,
            specialization_name=input_dto.specialization_name,
            is_primary=input_dto.is_primary,
            years_of_experience=input_dto.years_of_experience,
        )
        await self._specializations.add(specialization)
        self._uow.collect_events(specialization.pull_events())
        await self._uow.commit()

        return AddDoctorSpecializationOutput(
            specialization_id=specialization.id,
            doctor_id=specialization.doctor_id,
            specialization_name=specialization.specialization_name,
            is_primary=specialization.is_primary,
        )
