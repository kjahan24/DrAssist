"""Read-only queries against `Permission`.

Backs the module's public `PermissionQueryPort` — distinct from
`RbacPermissionService` (which resolves a *user's* effective permission
codes for authorization checks): this service exposes the permission
*catalog* itself, for a future admin UI to browse/filter permissions by
`resource`/`action` (see `domain/entities.py` for why those are derived,
stored columns) or for a future FHIR mapping layer to look up a
permission's metadata by code.
"""

from uuid import UUID

from app.modules.authentication.application.dto import PermissionSummaryDTO
from app.modules.authentication.domain.entities import Permission
from app.modules.authentication.domain.repositories import PermissionRepository


class PermissionQueryService:
    def __init__(self, *, permission_repository: PermissionRepository) -> None:
        self._permissions = permission_repository

    async def permission_exists(self, permission_id: UUID) -> bool:
        return await self._permissions.get_by_id(permission_id) is not None

    async def get_permission_summary(self, permission_id: UUID) -> PermissionSummaryDTO | None:
        permission = await self._permissions.get_by_id(permission_id)
        return _to_summary(permission) if permission is not None else None

    async def get_permission_by_code(self, code: str) -> PermissionSummaryDTO | None:
        permission = await self._permissions.get_by_code(code)
        return _to_summary(permission) if permission is not None else None

    async def list_all_permissions(self) -> list[PermissionSummaryDTO]:
        permissions = await self._permissions.list_all()
        return [_to_summary(permission) for permission in permissions]

    async def list_permissions_for_role(self, role_id: UUID) -> list[PermissionSummaryDTO]:
        permissions = await self._permissions.list_for_role(role_id)
        return [_to_summary(permission) for permission in permissions]


def _to_summary(permission: Permission) -> PermissionSummaryDTO:
    return PermissionSummaryDTO(
        permission_id=permission.id,
        code=str(permission.code),
        name=permission.name,
        description=permission.description,
        resource=permission.resource,
        action=permission.action,
    )
