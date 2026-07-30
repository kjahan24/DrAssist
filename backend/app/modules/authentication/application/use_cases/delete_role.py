"""`DeleteRole` — RBAC administration use case. "Role deletion is soft
delete only" — see `RoleRepository.delete()`. System roles cannot be
deleted, the same "cannot be modified" guard `Role.grant_permission()`/
`revoke_permission()`/`activate()`/`deactivate()` already enforce for
every other mutation.

`RoleDeleted` is collected directly rather than via `role.record_event()`
— deletion isn't modeled as a `Role` method, since `deleted_at` lives
only on the ORM row (see `domain/repositories.py`'s `delete()` docstring)
— the same direct-construction shape `AssignRoleToUser` already uses for
`UserRoleAssigned`.
"""

from app.modules.authentication.application.dto import DeleteRoleInput, DeleteRoleOutput
from app.modules.authentication.domain.events import RoleDeleted
from app.modules.authentication.domain.exceptions import RoleNotFoundError, SystemRoleImmutableError
from app.modules.authentication.domain.repositories import RoleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class DeleteRole(UseCase[DeleteRoleInput, DeleteRoleOutput]):
    def __init__(self, *, role_repository: RoleRepository, unit_of_work: UnitOfWork) -> None:
        self._roles = role_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: DeleteRoleInput) -> DeleteRoleOutput:
        role = await self._roles.get_by_id(input_dto.role_id)
        if role is None:
            raise RoleNotFoundError(input_dto.role_id)
        if role.is_system_role:
            raise SystemRoleImmutableError(role.id)

        await self._roles.delete(role.id)
        self._uow.collect_events(
            [RoleDeleted(role_id=role.id, organization_id=role.organization_id)]
        )
        await self._uow.commit()

        return DeleteRoleOutput(role_id=role.id)
