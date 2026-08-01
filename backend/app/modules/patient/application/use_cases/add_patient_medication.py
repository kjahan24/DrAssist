"""`AddPatientMedication` — a medication always belongs to an existing
patient. Unlike allergies, there is no duplicate-prevention rule here: "a
patient may have multiple medications" is an explicit business rule, so
no pre-check against existing rows is needed before adding a new one.

Depends on the Doctor module's public facade (`DoctorQueryPort`) to
confirm `prescribed_by` actually references a doctor when provided — the
same cross-module dependency pattern
`app.modules.patient.application.use_cases.record_patient_allergy.RecordPatientAllergy`
established for this module, reused here rather than inventing a new one
(see `docs/backend-architecture/10_module_communication.md`).
"""

from app.modules.doctor.public.exceptions import DoctorNotFoundError
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.application.dto import (
    AddPatientMedicationInput,
    AddPatientMedicationOutput,
)
from app.modules.patient.domain.entities import PatientMedication
from app.modules.patient.domain.exceptions import PatientNotFoundError
from app.modules.patient.domain.repositories import PatientMedicationRepository, PatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddPatientMedication(UseCase[AddPatientMedicationInput, AddPatientMedicationOutput]):
    def __init__(
        self,
        *,
        patient_medication_repository: PatientMedicationRepository,
        patient_repository: PatientRepository,
        doctor_query_port: DoctorQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._medications = patient_medication_repository
        self._patients = patient_repository
        self._doctors = doctor_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: AddPatientMedicationInput) -> AddPatientMedicationOutput:
        patient = await self._patients.get_by_id(input_dto.patient_id)
        if patient is None:
            raise PatientNotFoundError(input_dto.patient_id)

        if input_dto.prescribed_by is not None and not await self._doctors.doctor_exists(
            input_dto.prescribed_by
        ):
            raise DoctorNotFoundError(input_dto.prescribed_by)

        medication = PatientMedication.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name=input_dto.medication_name,
            dosage=input_dto.dosage,
            route=input_dto.route,
            start_date=input_dto.start_date,
            prescribed_by=input_dto.prescribed_by,
            generic_name=input_dto.generic_name,
            brand_name=input_dto.brand_name,
            dosage_unit=input_dto.dosage_unit,
            frequency=input_dto.frequency,
            indication=input_dto.indication,
            end_date=input_dto.end_date,
            is_current=input_dto.is_current,
            adherence_status=input_dto.adherence_status,
            instructions=input_dto.instructions,
            notes=input_dto.notes,
        )
        await self._medications.add(medication)
        self._uow.collect_events(medication.pull_events())
        await self._uow.commit()

        return AddPatientMedicationOutput(
            medication_id=medication.id,
            patient_id=medication.patient_id,
            medication_name=medication.medication_name,
            is_current=medication.is_current,
            adherence_status=medication.adherence_status,
        )
