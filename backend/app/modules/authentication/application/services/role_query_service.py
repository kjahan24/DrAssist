"""Read-only queries against `Role`.

Backs the module's public `RoleQueryPort` — added by the same task that
added `is_active`/organization-consistency validation (see
`use_cases/assign_role_to_user.py`), to give a future Hospital Admin
Portal / Super Admin Portal a way to list and inspect roles without
depending on this module's internal `RoleRepository` directly.
"""

from uuid import UUID

from app.modules.authentication.application.dto import RoleSummaryDTO
from app.modules.authentication.domain.entities import Role
from app.modules.authentication.domain.repositories import RoleRepository


class RoleQueryService:
    def __init__(self, *, role_repository: RoleRepository) -> None:
        self._roles = role_repository

    async def role_exists(self, role_id: UUID) -> bool:
        return await self._roles.get_by_id(role_id) is not None

    async def get_role_summary(self, role_id: UUID) -> RoleSummaryDTO | None:
        role = await self._roles.get_by_id(role_id)
        return _to_summary(role) if role is not None else None

    async def list_roles_for_organization(self, organization_id: UUID) -> list[RoleSummaryDTO]:
        roles = await self._roles.list_by_organization(organization_id)
        return [_to_summary(role) for role in roles]

    async def list_system_roles(self) -> list[RoleSummaryDTO]:
        roles = await self._roles.list_system_roles()
        return [_to_summary(role) for role in roles]


def _to_summary(role: Role) -> RoleSummaryDTO:
    return RoleSummaryDTO(
        role_id=role.id,
        organization_id=role.organization_id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        is_active=role.is_active,
    )
