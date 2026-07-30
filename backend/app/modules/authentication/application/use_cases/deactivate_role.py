"""`DeactivateRole` (is_active: True -> False). `Role.deactivate()` blocks
system roles — see `domain/entities.py`. Deactivating a role does not
revoke it from users who already hold it (that stays a separate,
explicit `RevokeRoleFromUser` action — not yet built, see `container.py`
scope note); it only makes the role ineligible for *new* assignments —
`AssignRoleToUser` rejects an inactive role via `InactiveRoleError`.
"""

from app.modules.authentication.application.dto import DeactivateRoleInput, RoleStatusOutput
from app.modules.authentication.domain.exceptions import RoleNotFoundError
from app.modules.authentication.domain.repositories import RoleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class DeactivateRole(UseCase[DeactivateRoleInput, RoleStatusOutput]):
    def __init__(self, *, role_repository: RoleRepository, unit_of_work: UnitOfWork) -> None:
        self._roles = role_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: DeactivateRoleInput) -> RoleStatusOutput:
        role = await self._roles.get_by_id(input_dto.role_id)
        if role is None:
            raise RoleNotFoundError(input_dto.role_id)

        role.deactivate()
        await self._roles.add(role)
        self._uow.collect_events(role.pull_events())
        await self._uow.commit()

        return RoleStatusOutput(role_id=role.id, is_active=role.is_active)
