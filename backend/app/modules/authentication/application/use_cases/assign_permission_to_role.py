"""`AssignPermissionToRole` — RBAC administration use case."""

from app.modules.authentication.application.dto import (
    AssignPermissionToRoleInput,
    AssignPermissionToRoleOutput,
)
from app.modules.authentication.domain.exceptions import (
    PermissionCodeNotRegisteredError,
    RoleNotFoundError,
)
from app.modules.authentication.domain.repositories import PermissionRepository, RoleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AssignPermissionToRole(UseCase[AssignPermissionToRoleInput, AssignPermissionToRoleOutput]):
    def __init__(
        self,
        *,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._roles = role_repository
        self._permissions = permission_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AssignPermissionToRoleInput) -> AssignPermissionToRoleOutput:
        role = await self._roles.get_by_id(input_dto.role_id)
        if role is None:
            raise RoleNotFoundError(input_dto.role_id)

        permission = await self._permissions.get_by_code(input_dto.permission_code)
        if permission is None:
            raise PermissionCodeNotRegisteredError(input_dto.permission_code)

        role.grant_permission(permission.id)
        await self._roles.add(role)
        self._uow.collect_events(role.pull_events())
        await self._uow.commit()

        return AssignPermissionToRoleOutput(
            role_id=role.id, permission_id=permission.id, permission_code=str(permission.code)
        )
