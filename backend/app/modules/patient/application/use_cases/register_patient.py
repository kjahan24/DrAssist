"""`RegisterPatient` — provisions a new `Patient` within an existing
organization.

Depends on the Organization module's public facade (`OrganizationQueryPort`)
to confirm the organization actually exists before registering the
patient — the same cross-module dependency pattern
`app.modules.doctor.application.use_cases.onboard_doctor.OnboardDoctor`
established for this codebase, reused here rather than inventing a new
one (see `docs/backend-architecture/10_module_communication.md`).
"""

from app.modules.organization.domain.exceptions import OrganizationNotFoundError
from app.modules.organization.public.interfaces import OrganizationQueryPort
from app.modules.patient.application.dto import RegisterPatientInput, RegisterPatientOutput
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.exceptions import DuplicatePatientNumberError
from app.modules.patient.domain.repositories import PatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


class RegisterPatient(UseCase[RegisterPatientInput, RegisterPatientOutput]):
    def __init__(
        self,
        *,
        patient_repository: PatientRepository,
        organization_query_port: OrganizationQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._patients = patient_repository
        self._organizations = organization_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RegisterPatientInput) -> RegisterPatientOutput:
        if not await self._organizations.organization_exists(input_dto.organization_id):
            raise OrganizationNotFoundError(input_dto.organization_id)

        existing = await self._patients.get_by_patient_number(
            organization_id=input_dto.organization_id, patient_number=input_dto.patient_number
        )
        if existing is not None:
            raise DuplicatePatientNumberError(input_dto.organization_id, input_dto.patient_number)

        patient = Patient.register(
            organization_id=input_dto.organization_id,
            patient_number=input_dto.patient_number,
            first_name=input_dto.first_name,
            last_name=input_dto.last_name,
            gender=input_dto.gender,
            date_of_birth=input_dto.date_of_birth,
            middle_name=input_dto.middle_name,
            preferred_name=input_dto.preferred_name,
            blood_group=input_dto.blood_group,
            marital_status=input_dto.marital_status,
            national_id=input_dto.national_id,
            passport_number=input_dto.passport_number,
            phone=PhoneNumber(input_dto.phone) if input_dto.phone else None,
            email=EmailAddress(input_dto.email) if input_dto.email else None,
            occupation=input_dto.occupation,
            nationality=input_dto.nationality,
            language=input_dto.language,
            religion=input_dto.religion,
            address_line_1=input_dto.address_line_1,
            address_line_2=input_dto.address_line_2,
            city=input_dto.city,
            state=input_dto.state,
            postal_code=input_dto.postal_code,
            country=input_dto.country,
            photo_url=input_dto.photo_url,
            remarks=input_dto.remarks,
        )

        await self._patients.add(patient)
        self._uow.collect_events(patient.pull_events())
        await self._uow.commit()

        return RegisterPatientOutput(
            patient_id=patient.id,
            organization_id=patient.organization_id,
            patient_number=patient.patient_number,
            status=patient.status,
        )
