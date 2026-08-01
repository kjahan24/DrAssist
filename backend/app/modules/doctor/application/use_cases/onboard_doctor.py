"""`OnboardDoctor` — provisions a new `Doctor` *and* its `DoctorProfile` in
one transaction (mirrors `CreateOrganization` provisioning
`OrganizationSettings` together with `Organization`).

Depends on the Organization and Authentication modules' public facades
(`OrganizationQueryPort`, `UserQueryPort`) to confirm the organization and
user actually exist before onboarding — the cross-module dependency
pattern documented in
`docs/backend-architecture/03_module_architecture.md` (Doctor "Depends
on") and `10_module_communication.md`, used here for the first time in
this codebase.
"""

from app.modules.authentication.public.exceptions import UserNotFoundError
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.doctor.application.dto import OnboardDoctorInput, OnboardDoctorOutput
from app.modules.doctor.domain.entities import Doctor, DoctorProfile
from app.modules.doctor.domain.exceptions import (
    DuplicateEmployeeIdError,
    UserAlreadyHasDoctorProfileError,
)
from app.modules.doctor.domain.repositories import DoctorProfileRepository, DoctorRepository
from app.modules.organization.public.exceptions import OrganizationNotFoundError
from app.modules.organization.public.interfaces import OrganizationQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase
from app.shared.domain.common_value_objects import EmailAddress


class OnboardDoctor(UseCase[OnboardDoctorInput, OnboardDoctorOutput]):
    def __init__(
        self,
        *,
        doctor_repository: DoctorRepository,
        doctor_profile_repository: DoctorProfileRepository,
        organization_query_port: OrganizationQueryPort,
        user_query_port: UserQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._doctors = doctor_repository
        self._profiles = doctor_profile_repository
        self._organizations = organization_query_port
        self._users = user_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: OnboardDoctorInput) -> OnboardDoctorOutput:
        if not await self._organizations.organization_exists(input_dto.organization_id):
            raise OrganizationNotFoundError(input_dto.organization_id)

        if not await self._users.user_exists(input_dto.user_id):
            raise UserNotFoundError(input_dto.user_id)

        existing_for_user = await self._doctors.get_by_user_id(input_dto.user_id)
        if existing_for_user is not None:
            raise UserAlreadyHasDoctorProfileError(input_dto.user_id)

        existing_for_code = await self._doctors.get_by_employee_id(
            organization_id=input_dto.organization_id, employee_id=input_dto.employee_id
        )
        if existing_for_code is not None:
            raise DuplicateEmployeeIdError(input_dto.organization_id, input_dto.employee_id)

        doctor = Doctor.create(
            organization_id=input_dto.organization_id,
            user_id=input_dto.user_id,
            employee_id=input_dto.employee_id,
            joining_date=input_dto.joining_date,
        )
        profile = DoctorProfile.create(
            doctor_id=doctor.id,
            full_name=input_dto.full_name,
            gender=input_dto.gender,
            date_of_birth=input_dto.date_of_birth,
            phone=input_dto.phone,
            email=EmailAddress(input_dto.email) if input_dto.email else None,
            address=input_dto.address,
            biography=input_dto.biography,
            years_of_experience=input_dto.years_of_experience,
            qualification=input_dto.qualification,
            consultation_fee=input_dto.consultation_fee,
            profile_photo_url=input_dto.profile_photo_url,
        )

        await self._doctors.add(doctor)
        await self._profiles.add(profile)

        self._uow.collect_events(doctor.pull_events())
        self._uow.collect_events(profile.pull_events())
        await self._uow.commit()

        return OnboardDoctorOutput(
            doctor_id=doctor.id,
            organization_id=doctor.organization_id,
            user_id=doctor.user_id,
            employee_id=doctor.employee_id,
            status=doctor.status,
            profile_id=profile.id,
        )
