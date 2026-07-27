"""Module-specific FastAPI dependency providers.

Constructs request-scoped repositories, the Unit of Work, and use cases
for this module — the wiring a future `api/endpoints/*.py` route module
will `Depends()` on. Every provider ultimately depends on
`app.api.deps.get_db_session`, so all repositories constructed for one
request share the same `AsyncSession` (and therefore the same
transaction) — see
`docs/backend-architecture/05_dependency_injection_and_lifecycle.md`.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.core.container import get_event_bus
from app.modules.organization.application.services.organization_query_service import (
    OrganizationQueryService,
)
from app.modules.organization.application.use_cases.create_department import CreateDepartment
from app.modules.organization.application.use_cases.create_organization import CreateOrganization
from app.modules.organization.application.use_cases.update_organization_settings import (
    UpdateOrganizationSettings,
)
from app.modules.organization.domain.repositories import (
    DepartmentRepository,
    OrganizationRepository,
    OrganizationSettingsRepository,
)
from app.modules.organization.infrastructure.repositories import (
    SqlAlchemyDepartmentRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyOrganizationSettingsRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_organization_repository(session: DbSession) -> OrganizationRepository:
    return SqlAlchemyOrganizationRepository(session)


def get_organization_settings_repository(session: DbSession) -> OrganizationSettingsRepository:
    return SqlAlchemyOrganizationSettingsRepository(session)


def get_department_repository(session: DbSession) -> DepartmentRepository:
    return SqlAlchemyDepartmentRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


OrganizationRepo = Annotated[OrganizationRepository, Depends(get_organization_repository)]
OrganizationSettingsRepo = Annotated[
    OrganizationSettingsRepository, Depends(get_organization_settings_repository)
]
DepartmentRepo = Annotated[DepartmentRepository, Depends(get_department_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_organization_query_service(
    organization_repository: OrganizationRepo,
    organization_settings_repository: OrganizationSettingsRepo,
) -> OrganizationQueryService:
    return OrganizationQueryService(
        organization_repository=organization_repository,
        organization_settings_repository=organization_settings_repository,
    )


def get_create_organization_use_case(
    organization_repository: OrganizationRepo,
    organization_settings_repository: OrganizationSettingsRepo,
    unit_of_work: Uow,
) -> CreateOrganization:
    return CreateOrganization(
        organization_repository=organization_repository,
        organization_settings_repository=organization_settings_repository,
        unit_of_work=unit_of_work,
    )


def get_update_organization_settings_use_case(
    organization_settings_repository: OrganizationSettingsRepo, unit_of_work: Uow
) -> UpdateOrganizationSettings:
    return UpdateOrganizationSettings(
        organization_settings_repository=organization_settings_repository,
        unit_of_work=unit_of_work,
    )


def get_create_department_use_case(
    department_repository: DepartmentRepo,
    organization_repository: OrganizationRepo,
    unit_of_work: Uow,
) -> CreateDepartment:
    return CreateDepartment(
        department_repository=department_repository,
        organization_repository=organization_repository,
        unit_of_work=unit_of_work,
    )
