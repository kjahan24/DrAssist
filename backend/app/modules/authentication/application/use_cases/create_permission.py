"""`CreatePermission` — RBAC administration use case. "Permission codes
must be globally unique" is checked via `PermissionRepository
.get_by_code()` before construction, the identical "query first, then
construct" technique `CreateRole` already uses for its own duplicate-name
prevention, additionally backed by the database-level `uq_permissions_code`
partial unique index (see `infrastructure/models.py`).
"""

from app.modules.authentication.application.dto import (
    CreatePermissionInput,
    CreatePermissionOutput,
)
from app.modules.authentication.domain.entities import Permission
from app.modules.authentication.domain.exceptions import DuplicatePermissionCodeError
from app.modules.authentication.domain.repositories import PermissionRepository
from app.modules.authentication.domain.value_objects import PermissionCode
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreatePermission(UseCase[CreatePermissionInput, CreatePermissionOutput]):
    def __init__(
        self, *, permission_repository: PermissionRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._permissions = permission_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: CreatePermissionInput) -> CreatePermissionOutput:
        code = PermissionCode(input_dto.code)

        existing = await self._permissions.get_by_code(str(code))
        if existing is not None:
            raise DuplicatePermissionCodeError(str(code))

        permission = Permission.create(
            code=code, name=input_dto.name, description=input_dto.description
        )
        await self._permissions.add(permission)
        self._uow.collect_events(permission.pull_events())
        await self._uow.commit()

        return CreatePermissionOutput(
            permission_id=permission.id,
            code=str(permission.code),
            resource=permission.resource,
            action=permission.action,
        )
