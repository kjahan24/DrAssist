"""`AssignRoleToUser` — RBAC administration use case.

A later task ("Implement the RBAC module") found this use case checked
neither "UserRole assignments must preserve organization consistency"
(a role scoped to one organization could be assigned to a user in
another) nor "Inactive roles cannot be assigned" (`Role.is_active` did
not exist when this use case was first written) and added both checks
here — the natural, and only, place to enforce them: they are
cross-aggregate rules (`Role` vs. the assignment's own `organization_id`)
that neither `Role` nor `User` can enforce alone. A system role
(`organization_id is None`) is exempt from the organization-consistency
check by design — it is deliberately assignable to a user in *any*
organization.
"""

from datetime import UTC, datetime

from app.modules.authentication.application.dto import (
    AssignRoleToUserInput,
    AssignRoleToUserOutput,
)
from app.modules.authentication.domain.events import UserRoleAssigned
from app.modules.authentication.domain.exceptions import (
    InactiveRoleError,
    RoleNotFoundError,
    RoleOrganizationMismatchError,
    UserNotFoundError,
)
from app.modules.authentication.domain.repositories import RoleRepository, UserRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AssignRoleToUser(UseCase[AssignRoleToUserInput, AssignRoleToUserOutput]):
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._users = user_repository
        self._roles = role_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AssignRoleToUserInput) -> AssignRoleToUserOutput:
        user = await self._users.get_by_id(input_dto.user_id)
        if user is None or user.organization_id != input_dto.organization_id:
            raise UserNotFoundError(input_dto.user_id)

        role = await self._roles.get_by_id(input_dto.role_id)
        if role is None:
            raise RoleNotFoundError(input_dto.role_id)
        if role.organization_id is not None and role.organization_id != input_dto.organization_id:
            raise RoleOrganizationMismatchError(role.id, input_dto.organization_id)
        if not role.is_active:
            raise InactiveRoleError(role.id)

        now = datetime.now(UTC)
        await self._roles.assign_to_user(
            organization_id=input_dto.organization_id,
            user_id=input_dto.user_id,
            role_id=input_dto.role_id,
            granted_by=input_dto.granted_by,
            granted_at=now,
        )
        self._uow.collect_events(
            [
                UserRoleAssigned(
                    user_id=input_dto.user_id,
                    organization_id=input_dto.organization_id,
                    role_id=input_dto.role_id,
                    granted_by=input_dto.granted_by,
                )
            ]
        )
        await self._uow.commit()

        return AssignRoleToUserOutput(user_id=input_dto.user_id, role_id=input_dto.role_id)
