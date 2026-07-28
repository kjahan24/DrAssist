"""`AddDoctorLicense` — a license always belongs to an existing doctor, and
`license_number` is unique across the whole table (not just per doctor)."""

from app.modules.doctor.application.dto import AddDoctorLicenseInput, AddDoctorLicenseOutput
from app.modules.doctor.domain.entities import DoctorLicense
from app.modules.doctor.domain.exceptions import DoctorNotFoundError, DuplicateLicenseNumberError
from app.modules.doctor.domain.repositories import DoctorLicenseRepository, DoctorRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddDoctorLicense(UseCase[AddDoctorLicenseInput, AddDoctorLicenseOutput]):
    def __init__(
        self,
        *,
        doctor_license_repository: DoctorLicenseRepository,
        doctor_repository: DoctorRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._licenses = doctor_license_repository
        self._doctors = doctor_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AddDoctorLicenseInput) -> AddDoctorLicenseOutput:
        doctor = await self._doctors.get_by_id(input_dto.doctor_id)
        if doctor is None:
            raise DoctorNotFoundError(input_dto.doctor_id)

        existing = await self._licenses.get_by_license_number(input_dto.license_number)
        if existing is not None:
            raise DuplicateLicenseNumberError(input_dto.license_number)

        license_ = DoctorLicense.create(
            doctor_id=doctor.id,
            license_number=input_dto.license_number,
            issuing_authority=input_dto.issuing_authority,
            country=input_dto.country,
            issue_date=input_dto.issue_date,
            expiry_date=input_dto.expiry_date,
        )
        await self._licenses.add(license_)
        self._uow.collect_events(license_.pull_events())
        await self._uow.commit()

        return AddDoctorLicenseOutput(
            license_id=license_.id,
            doctor_id=license_.doctor_id,
            license_number=license_.license_number,
            verification_status=license_.verification_status,
        )
