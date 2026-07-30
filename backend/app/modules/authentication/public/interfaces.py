"""The Authentication module's public ports — the only contracts another
module (or `app/api/deps.py`) may depend on. See
`docs/backend-architecture/03_module_architecture.md` (Authentication) and
`10_module_communication.md`.

Never import from `app.modules.authentication.domain`,
`.application` (beyond this package), or `.infrastructure` from outside
this module — this file, `dto.py`, and `events.py` (not yet needed by any
other module, so not added until one exists) are the entire allowed
surface.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.authentication.public.dto import (
    AuthenticatedPrincipalDTO,
    PermissionSummaryDTO,
    RoleSummaryDTO,
    UserSummaryDTO,
)


class UserQueryPort(ABC):
    @abstractmethod
    async def user_exists(self, user_id: UUID) -> bool: ...

    @abstractmethod
    async def get_user_summary(self, user_id: UUID) -> UserSummaryDTO | None: ...


class PermissionCheckPort(ABC):
    @abstractmethod
    async def has_permission(self, user_id: UUID, permission_code: str) -> bool: ...

    @abstractmethod
    async def get_effective_permission_codes(self, user_id: UUID) -> frozenset[str]: ...


class RoleQueryPort(ABC):
    """Added by the task that added `Role.is_active` — the contract a
    future Hospital Admin Portal / Super Admin Portal, or any other
    module, depends on to read the role catalog without importing this
    module's internals."""

    @abstractmethod
    async def role_exists(self, role_id: UUID) -> bool: ...

    @abstractmethod
    async def get_role_summary(self, role_id: UUID) -> RoleSummaryDTO | None: ...

    @abstractmethod
    async def list_roles_for_organization(self, organization_id: UUID) -> list[RoleSummaryDTO]: ...

    @abstractmethod
    async def list_system_roles(self) -> list[RoleSummaryDTO]: ...


class PermissionQueryPort(ABC):
    """The permission *catalog*, as opposed to `PermissionCheckPort`
    (a specific user's effective permissions)."""

    @abstractmethod
    async def permission_exists(self, permission_id: UUID) -> bool: ...

    @abstractmethod
    async def get_permission_summary(self, permission_id: UUID) -> PermissionSummaryDTO | None: ...

    @abstractmethod
    async def get_permission_by_code(self, code: str) -> PermissionSummaryDTO | None: ...

    @abstractmethod
    async def list_all_permissions(self) -> list[PermissionSummaryDTO]: ...

    @abstractmethod
    async def list_permissions_for_role(self, role_id: UUID) -> list[PermissionSummaryDTO]: ...


class AccessTokenValidationPort(ABC):
    """Reached today only by `app/api/deps.py` (not by another module yet) —
    kept as a formal port rather than an ad hoc facade method for the same
    reason repositories get interfaces: `get_current_user` is exactly the
    kind of call site that benefits from depending on an abstraction it
    can fake in tests, and this is the seam a future
    `app/modules/<other>/` module would also use if it ever needed to
    validate a token itself rather than trusting an already-resolved
    principal passed down to it.
    """

    @abstractmethod
    async def get_authenticated_principal(self, raw_access_token: str) -> AuthenticatedPrincipalDTO:
        """Raises `app.modules.authentication.application.exceptions.AuthenticationError`
        if the token is invalid, expired, or resolves to a user/session
        that can no longer authenticate."""
        ...
