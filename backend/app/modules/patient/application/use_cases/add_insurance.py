"""`AddInsurance` — an insurance record always belongs to an existing
patient. `expiry_date > effective_date` is enforced by `Insurance`'s own
`__post_init__`, mirroring
`app.modules.doctor.domain.entities.DoctorLicense`'s issue/expiry check."""

from app.modules.patient.application.dto import AddInsuranceInput, AddInsuranceOutput
from app.modules.patient.domain.entities import Insurance
from app.modules.patient.domain.exceptions import PatientNotFoundError
from app.modules.patient.domain.repositories import InsuranceRepository, PatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddInsurance(UseCase[AddInsuranceInput, AddInsuranceOutput]):
    def __init__(
        self,
        *,
        insurance_repository: InsuranceRepository,
        patient_repository: PatientRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._insurance = insurance_repository
        self._patients = patient_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AddInsuranceInput) -> AddInsuranceOutput:
        patient = await self._patients.get_by_id(input_dto.patient_id)
        if patient is None:
            raise PatientNotFoundError(input_dto.patient_id)

        insurance = Insurance.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            provider_name=input_dto.provider_name,
            policy_number=input_dto.policy_number,
            effective_date=input_dto.effective_date,
            expiry_date=input_dto.expiry_date,
            member_id=input_dto.member_id,
            group_number=input_dto.group_number,
            coverage_type=input_dto.coverage_type,
        )
        await self._insurance.add(insurance)
        self._uow.collect_events(insurance.pull_events())
        await self._uow.commit()

        return AddInsuranceOutput(
            insurance_id=insurance.id,
            patient_id=insurance.patient_id,
            policy_number=insurance.policy_number,
            status=insurance.status,
        )
