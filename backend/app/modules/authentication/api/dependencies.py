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
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings, get_settings
from app.core.container import get_event_bus
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.application.use_cases.assign_permission_to_role import (
    AssignPermissionToRole,
)
from app.modules.authentication.application.use_cases.assign_role_to_user import (
    AssignRoleToUser,
)
from app.modules.authentication.application.use_cases.create_role import CreateRole
from app.modules.authentication.domain.repositories import (
    PermissionRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
    UserSessionRepository,
)
from app.modules.authentication.infrastructure.repositories import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserSessionRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_user_repository(session: DbSession) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_role_repository(session: DbSession) -> RoleRepository:
    return SqlAlchemyRoleRepository(session)


def get_permission_repository(session: DbSession) -> PermissionRepository:
    return SqlAlchemyPermissionRepository(session)


def get_user_session_repository(session: DbSession) -> UserSessionRepository:
    return SqlAlchemyUserSessionRepository(session)


def get_refresh_token_repository(session: DbSession) -> RefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(session)


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
RoleRepo = Annotated[RoleRepository, Depends(get_role_repository)]
PermissionRepo = Annotated[PermissionRepository, Depends(get_permission_repository)]
Uow = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_permission_service(
    role_repository: RoleRepo, permission_repository: PermissionRepo
) -> RbacPermissionService:
    return RbacPermissionService(
        role_repository=role_repository, permission_repository=permission_repository
    )


def get_create_role_use_case(role_repository: RoleRepo, unit_of_work: Uow) -> CreateRole:
    return CreateRole(role_repository=role_repository, unit_of_work=unit_of_work)


def get_assign_permission_to_role_use_case(
    role_repository: RoleRepo, permission_repository: PermissionRepo, unit_of_work: Uow
) -> AssignPermissionToRole:
    return AssignPermissionToRole(
        role_repository=role_repository,
        permission_repository=permission_repository,
        unit_of_work=unit_of_work,
    )


def get_assign_role_to_user_use_case(
    user_repository: UserRepo, role_repository: RoleRepo, unit_of_work: Uow
) -> AssignRoleToUser:
    return AssignRoleToUser(
        user_repository=user_repository, role_repository=role_repository, unit_of_work=unit_of_work
    )


def get_jwt_settings(settings: Annotated[Settings, Depends(get_settings)]) -> tuple[str, str]:
    """`(secret_key, algorithm)` — the two values token encode/decode need,
    kept out of every call site's direct `get_settings()` dependency so
    swapping the settings source later touches only this function."""
    return settings.backend.secret_key, settings.jwt.algorithm
