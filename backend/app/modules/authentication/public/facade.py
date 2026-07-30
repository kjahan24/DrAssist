"""`AuthenticationFacade` — the one concrete implementation of every port
in `public/interfaces.py`. Constructed per-request by
`app.modules.authentication.container.build_authentication_facade`, bound
to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.authentication.application.dto import (
    AuthenticatedPrincipalDTO,
    PermissionSummaryDTO,
    RoleSummaryDTO,
    UserSummaryDTO,
)
from app.modules.authentication.application.services.permission_query_service import (
    PermissionQueryService,
)
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.application.services.role_query_service import RoleQueryService
from app.modules.authentication.application.services.token_validation_service import (
    ValidateAccessToken,
    ValidateAccessTokenInput,
)
from app.modules.authentication.domain.repositories import UserRepository, UserSessionRepository
from app.modules.authentication.public.interfaces import (
    AccessTokenValidationPort,
    PermissionCheckPort,
    PermissionQueryPort,
    RoleQueryPort,
    UserQueryPort,
)


class AuthenticationFacade(
    UserQueryPort,
    PermissionCheckPort,
    AccessTokenValidationPort,
    RoleQueryPort,
    PermissionQueryPort,
):
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        user_session_repository: UserSessionRepository,
        permission_service: RbacPermissionService,
        role_query_service: RoleQueryService,
        permission_query_service: PermissionQueryService,
        secret_key: str,
        algorithm: str,
    ) -> None:
        self._users = user_repository
        self._permission_service = permission_service
        self._role_query_service = role_query_service
        self._permission_query_service = permission_query_service
        self._validate_access_token = ValidateAccessToken(
            user_repository=user_repository,
            user_session_repository=user_session_repository,
            permission_service=permission_service,
            secret_key=secret_key,
            algorithm=algorithm,
        )

    async def user_exists(self, user_id: UUID) -> bool:
        return await self._users.get_by_id(user_id) is not None

    async def get_user_summary(self, user_id: UUID) -> UserSummaryDTO | None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            return None
        return UserSummaryDTO(
            user_id=user.id,
            organization_id=user.organization_id,
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
        )

    async def has_permission(self, user_id: UUID, permission_code: str) -> bool:
        return await self._permission_service.has_permission(user_id, permission_code)

    async def get_effective_permission_codes(self, user_id: UUID) -> frozenset[str]:
        return await self._permission_service.get_effective_permission_codes(user_id)

    async def get_authenticated_principal(self, raw_access_token: str) -> AuthenticatedPrincipalDTO:
        return await self._validate_access_token.execute(
            ValidateAccessTokenInput(raw_token=raw_access_token)
        )

    async def role_exists(self, role_id: UUID) -> bool:
        return await self._role_query_service.role_exists(role_id)

    async def get_role_summary(self, role_id: UUID) -> RoleSummaryDTO | None:
        return await self._role_query_service.get_role_summary(role_id)

    async def list_roles_for_organization(self, organization_id: UUID) -> list[RoleSummaryDTO]:
        return await self._role_query_service.list_roles_for_organization(organization_id)

    async def list_system_roles(self) -> list[RoleSummaryDTO]:
        return await self._role_query_service.list_system_roles()

    async def permission_exists(self, permission_id: UUID) -> bool:
        return await self._permission_query_service.permission_exists(permission_id)

    async def get_permission_summary(self, permission_id: UUID) -> PermissionSummaryDTO | None:
        return await self._permission_query_service.get_permission_summary(permission_id)

    async def get_permission_by_code(self, code: str) -> PermissionSummaryDTO | None:
        return await self._permission_query_service.get_permission_by_code(code)

    async def list_all_permissions(self) -> list[PermissionSummaryDTO]:
        return await self._permission_query_service.list_all_permissions()

    async def list_permissions_for_role(self, role_id: UUID) -> list[PermissionSummaryDTO]:
        return await self._permission_query_service.list_permissions_for_role(role_id)
