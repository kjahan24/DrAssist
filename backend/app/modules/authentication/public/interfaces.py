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

from app.modules.authentication.public.dto import AuthenticatedPrincipalDTO, UserSummaryDTO


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
