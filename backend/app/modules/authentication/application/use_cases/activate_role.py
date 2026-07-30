"""`ActivateRole` (is_active: False -> True). `Role.activate()` blocks
system roles — see `domain/entities.py`."""

from app.modules.authentication.application.dto import ActivateRoleInput, RoleStatusOutput
from app.modules.authentication.domain.exceptions import RoleNotFoundError
from app.modules.authentication.domain.repositories import RoleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ActivateRole(UseCase[ActivateRoleInput, RoleStatusOutput]):
    def __init__(self, *, role_repository: RoleRepository, unit_of_work: UnitOfWork) -> None:
        self._roles = role_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: ActivateRoleInput) -> RoleStatusOutput:
        role = await self._roles.get_by_id(input_dto.role_id)
        if role is None:
            raise RoleNotFoundError(input_dto.role_id)

        role.activate()
        await self._roles.add(role)
        self._uow.collect_events(role.pull_events())
        await self._uow.commit()

        return RoleStatusOutput(role_id=role.id, is_active=role.is_active)
