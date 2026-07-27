"""RBAC effective-permission resolution.

Backs the module's public `PermissionCheckPort`
(`docs/backend-architecture/03_module_architecture.md`). A user's
effective permissions are the union of every permission granted by every
role assigned to them. This is a pure query service (no mutation, no Unit
of Work needed) — per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance, it doesn't need its own bespoke ABC since
`PermissionCheckPort` (in `public/interfaces.py`) already is that
interface; this class is the one implementation.

Not cached here — production deployments should wrap this behind a
Redis-backed cache keyed by `user_id`, invalidated on role/permission
change events (`docs/backend-architecture/07_security_layer.md §2`); left
as a documented extension point rather than built now; caching every user
on every request from day one is what's called speculative complexity.
"""

from uuid import UUID

from app.modules.authentication.domain.repositories import PermissionRepository, RoleRepository


class RbacPermissionService:
    def __init__(
        self,
        *,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
    ) -> None:
        self._roles = role_repository
        self._permissions = permission_repository

    async def get_effective_permission_codes(self, user_id: UUID) -> frozenset[str]:
        roles = await self._roles.list_for_user(user_id)
        codes: set[str] = set()
        for role in roles:
            role_permissions = await self._permissions.list_for_role(role.id)
            codes.update(str(permission.code) for permission in role_permissions)
        return frozenset(codes)

    async def has_permission(self, user_id: UUID, permission_code: str) -> bool:
        codes = await self.get_effective_permission_codes(user_id)
        return permission_code in codes
