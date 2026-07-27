"""`CreateRole` — RBAC administration use case (not login/register, which
this task deliberately excludes; see module container docstring).
"""

from app.modules.authentication.application.dto import CreateRoleInput, CreateRoleOutput
from app.modules.authentication.domain.entities import Role
from app.modules.authentication.domain.exceptions import DuplicateRoleNameError
from app.modules.authentication.domain.repositories import RoleRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateRole(UseCase[CreateRoleInput, CreateRoleOutput]):
    def __init__(self, *, role_repository: RoleRepository, unit_of_work: UnitOfWork) -> None:
        self._roles = role_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateRoleInput) -> CreateRoleOutput:
        existing = (
            await self._roles.get_system_role_by_name(input_dto.name)
            if input_dto.organization_id is None
            else await self._roles.get_org_role_by_name(
                organization_id=input_dto.organization_id, name=input_dto.name
            )
        )
        if existing is not None:
            raise DuplicateRoleNameError(input_dto.name)

        role = Role.create(
            organization_id=input_dto.organization_id,
            name=input_dto.name,
            description=input_dto.description,
            is_system_role=input_dto.is_system_role,
        )
        await self._roles.add(role)
        self._uow.collect_events(role.pull_events())
        await self._uow.commit()

        return CreateRoleOutput(
            role_id=role.id, organization_id=role.organization_id, name=role.name
        )
