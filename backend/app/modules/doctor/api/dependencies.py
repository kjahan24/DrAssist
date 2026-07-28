"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.

`OnboardDoctor` additionally needs the Organization and Authentication
modules' public facades; those are built via their own
`build_organization_facade`/`build_authentication_facade` composition
roots (bound to the same `session`) rather than duplicating facade
construction here.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.authentication.container import build_authentication_facade
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.doctor.application.services.doctor_query_service import DoctorQueryService
from app.modules.doctor.application.use_cases.add_doctor_license import AddDoctorLicense
from app.modules.doctor.application.use_cases.add_doctor_schedule import AddDoctorSchedule
from app.modules.doctor.application.use_cases.add_doctor_specialization import (
    AddDoctorSpecialization,
)
from app.modules.doctor.application.use_cases.onboard_doctor import OnboardDoctor
from app.modules.doctor.domain.repositories import (
    DoctorLicenseRepository,
    DoctorProfileRepository,
    DoctorRepository,
    DoctorScheduleRepository,
    DoctorSpecializationRepository,
)
from app.modules.doctor.infrastructure.repositories import (
    SqlAlchemyDoctorLicenseRepository,
    SqlAlchemyDoctorProfileRepository,
    SqlAlchemyDoctorRepository,
    SqlAlchemyDoctorScheduleRepository,
    SqlAlchemyDoctorSpecializationRepository,
)
from app.modules.organization.container import build_organization_facade
from app.modules.organization.public.interfaces import OrganizationQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_doctor_repository(session: DbSession) -> DoctorRepository:
    return SqlAlchemyDoctorRepository(session)


def get_doctor_profile_repository(session: DbSession) -> DoctorProfileRepository:
    return SqlAlchemyDoctorProfileRepository(session)


def get_doctor_license_repository(session: DbSession) -> DoctorLicenseRepository:
    return SqlAlchemyDoctorLicenseRepository(session)


def get_doctor_specialization_repository(session: DbSession) -> DoctorSpecializationRepository:
    return SqlAlchemyDoctorSpecializationRepository(session)


def get_doctor_schedule_repository(session: DbSession) -> DoctorScheduleRepository:
    return SqlAlchemyDoctorScheduleRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


def get_organization_query_port(session: DbSession) -> OrganizationQueryPort:
    return build_organization_facade(session)


def get_user_query_port(session: DbSession) -> UserQueryPort:
    return build_authentication_facade(session)


DoctorRepo = Annotated[DoctorRepository, Depends(get_doctor_repository)]
DoctorProfileRepo = Annotated[DoctorProfileRepository, Depends(get_doctor_profile_repository)]
DoctorLicenseRepo = Annotated[DoctorLicenseRepository, Depends(get_doctor_license_repository)]
DoctorSpecializationRepo = Annotated[
    DoctorSpecializationRepository, Depends(get_doctor_specialization_repository)
]
DoctorScheduleRepo = Annotated[DoctorScheduleRepository, Depends(get_doctor_schedule_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]
OrgQueryPort = Annotated[OrganizationQueryPort, Depends(get_organization_query_port)]
UserPort = Annotated[UserQueryPort, Depends(get_user_query_port)]


def get_doctor_query_service(doctor_repository: DoctorRepo) -> DoctorQueryService:
    return DoctorQueryService(doctor_repository=doctor_repository)


def get_onboard_doctor_use_case(
    doctor_repository: DoctorRepo,
    doctor_profile_repository: DoctorProfileRepo,
    organization_query_port: OrgQueryPort,
    user_query_port: UserPort,
    unit_of_work: Uow,
) -> OnboardDoctor:
    return OnboardDoctor(
        doctor_repository=doctor_repository,
        doctor_profile_repository=doctor_profile_repository,
        organization_query_port=organization_query_port,
        user_query_port=user_query_port,
        unit_of_work=unit_of_work,
    )


def get_add_doctor_license_use_case(
    doctor_license_repository: DoctorLicenseRepo,
    doctor_repository: DoctorRepo,
    unit_of_work: Uow,
) -> AddDoctorLicense:
    return AddDoctorLicense(
        doctor_license_repository=doctor_license_repository,
        doctor_repository=doctor_repository,
        unit_of_work=unit_of_work,
    )


def get_add_doctor_specialization_use_case(
    doctor_specialization_repository: DoctorSpecializationRepo,
    doctor_repository: DoctorRepo,
    unit_of_work: Uow,
) -> AddDoctorSpecialization:
    return AddDoctorSpecialization(
        doctor_specialization_repository=doctor_specialization_repository,
        doctor_repository=doctor_repository,
        unit_of_work=unit_of_work,
    )


def get_add_doctor_schedule_use_case(
    doctor_schedule_repository: DoctorScheduleRepo,
    doctor_repository: DoctorRepo,
    unit_of_work: Uow,
) -> AddDoctorSchedule:
    return AddDoctorSchedule(
        doctor_schedule_repository=doctor_schedule_repository,
        doctor_repository=doctor_repository,
        unit_of_work=unit_of_work,
    )
