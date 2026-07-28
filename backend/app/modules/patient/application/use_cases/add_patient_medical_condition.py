"""`AddPatientMedicalCondition` — a condition always belongs to an
existing patient, and (same patient + condition name) must not have two
active condition records at once — the same "duplicate active" pattern
`app.modules.patient.application.use_cases.record_patient_allergy.RecordPatientAllergy`
established for this module.

Depends on the Doctor module's public facade (`DoctorQueryPort`) to
confirm `diagnosed_by` actually references a doctor when provided — the
same cross-module dependency pattern already used by `RecordPatientAllergy`
and
`app.modules.patient.application.use_cases.add_patient_medication.AddPatientMedication`
(see `docs/backend-architecture/10_module_communication.md`).
"""

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.application.dto import (
    AddPatientMedicalConditionInput,
    AddPatientMedicalConditionOutput,
)
from app.modules.patient.domain.entities import PatientMedicalCondition
from app.modules.patient.domain.exceptions import (
    DuplicateActiveConditionError,
    PatientNotFoundError,
)
from app.modules.patient.domain.repositories import (
    PatientMedicalConditionRepository,
    PatientRepository,
)
from app.modules.patient.domain.value_objects import ICD10Code
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddPatientMedicalCondition(
    UseCase[AddPatientMedicalConditionInput, AddPatientMedicalConditionOutput]
):
    def __init__(
        self,
        *,
        patient_medical_condition_repository: PatientMedicalConditionRepository,
        patient_repository: PatientRepository,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._conditions = patient_medical_condition_repository
        self._patients = patient_repository
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(
        self, input_dto: AddPatientMedicalConditionInput
    ) -> AddPatientMedicalConditionOutput:
        patient = await self._patients.get_by_id(input_dto.patient_id)
        if patient is None:
            raise PatientNotFoundError(input_dto.patient_id)

        if input_dto.diagnosed_by is not None and not await self._doctors.doctor_exists(
            input_dto.diagnosed_by
        ):
            raise DoctorNotFoundError(input_dto.diagnosed_by)

        existing_active = await self._conditions.get_active_by_patient_and_condition_name(
            patient_id=patient.id, condition_name=input_dto.condition_name
        )
        if existing_active is not None:
            raise DuplicateActiveConditionError(patient.id, input_dto.condition_name)

        condition = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name=input_dto.condition_name,
            category=input_dto.category,
            severity=input_dto.severity,
            diagnosis_date=input_dto.diagnosis_date,
            diagnosed_by=input_dto.diagnosed_by,
            icd10_code=ICD10Code(input_dto.icd10_code) if input_dto.icd10_code else None,
            onset_date=input_dto.onset_date,
            status=input_dto.status,
            is_chronic=input_dto.is_chronic,
            is_infectious=input_dto.is_infectious,
            notes=input_dto.notes,
            resolved_date=input_dto.resolved_date,
        )
        await self._conditions.add(condition)
        self._uow.collect_events(condition.pull_events())
        await self._uow.commit()

        return AddPatientMedicalConditionOutput(
            condition_id=condition.id,
            patient_id=condition.patient_id,
            condition_name=condition.condition_name,
            status=condition.status,
        )
