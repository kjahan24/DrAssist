"""`RecordPatientAllergy` — an allergy always belongs to an existing
patient, and (same patient + allergen) must not have two active allergy
records at once.

Depends on the Doctor module's public facade (`DoctorQueryPort`) to
confirm `verified_by` actually references a doctor when provided — the
same cross-module dependency pattern
`app.modules.doctor.application.use_cases.onboard_doctor.OnboardDoctor`
and
`app.modules.patient.application.use_cases.register_patient.RegisterPatient`
established for this codebase, reused here rather than inventing a new
one (see `docs/backend-architecture/10_module_communication.md`).
"""

from app.modules.doctor.public.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.application.dto import (
    RecordPatientAllergyInput,
    RecordPatientAllergyOutput,
)
from app.modules.patient.domain.entities import PatientAllergy
from app.modules.patient.domain.exceptions import DuplicateActiveAllergyError, PatientNotFoundError
from app.modules.patient.domain.repositories import PatientAllergyRepository, PatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RecordPatientAllergy(UseCase[RecordPatientAllergyInput, RecordPatientAllergyOutput]):
    def __init__(
        self,
        *,
        patient_allergy_repository: PatientAllergyRepository,
        patient_repository: PatientRepository,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._allergies = patient_allergy_repository
        self._patients = patient_repository
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RecordPatientAllergyInput) -> RecordPatientAllergyOutput:
        patient = await self._patients.get_by_id(input_dto.patient_id)
        if patient is None:
            raise PatientNotFoundError(input_dto.patient_id)

        if input_dto.verified_by is not None and not await self._doctors.doctor_exists(
            input_dto.verified_by
        ):
            raise DoctorNotFoundError(input_dto.verified_by)

        existing_active = await self._allergies.get_active_by_patient_and_allergen(
            patient_id=patient.id, allergen_name=input_dto.allergen_name
        )
        if existing_active is not None:
            raise DuplicateActiveAllergyError(patient.id, input_dto.allergen_name)

        allergy = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=input_dto.allergy_type,
            allergen_name=input_dto.allergen_name,
            severity=input_dto.severity,
            reaction=input_dto.reaction,
            onset_date=input_dto.onset_date,
            notes=input_dto.notes,
            verified_by=input_dto.verified_by,
            verified_date=input_dto.verified_date,
        )
        await self._allergies.add(allergy)
        self._uow.collect_events(allergy.pull_events())
        await self._uow.commit()

        return RecordPatientAllergyOutput(
            allergy_id=allergy.id,
            patient_id=allergy.patient_id,
            allergen_name=allergy.allergen_name,
            severity=allergy.severity,
            status=allergy.status,
        )
