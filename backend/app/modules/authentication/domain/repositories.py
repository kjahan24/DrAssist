"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.authentication.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

There is no `update()` method: a repository returns the actual aggregate
object, the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.modules.authentication.domain.entities import (
    Permission,
    RefreshToken,
    Role,
    User,
    UserSession,
)
from app.shared.domain.common_value_objects import EmailAddress


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, *, organization_id: UUID, email: EmailAddress) -> User | None: ...

    @abstractmethod
    async def list_by_organization(
        self, *, organization_id: UUID, offset: int = 0, limit: int = 20
    ) -> list[User]: ...

    @abstractmethod
    async def add(self, user: User) -> None: ...


class RoleRepository(ABC):
    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Role | None: ...

    @abstractmethod
    async def get_system_role_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    async def get_org_role_by_name(self, *, organization_id: UUID, name: str) -> Role | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: UUID) -> list[Role]: ...

    @abstractmethod
    async def list_by_organization(self, organization_id: UUID) -> list[Role]: ...

    @abstractmethod
    async def list_system_roles(self) -> list[Role]: ...

    @abstractmethod
    async def add(self, role: Role) -> None: ...

    @abstractmethod
    async def delete(self, role_id: UUID) -> None:
        """Soft delete: sets `deleted_at`. Mirrors `revoke_from_user`'s
        direct-model-mutation shape below — a full aggregate still gets no
        separate `update()` method (see module docstring), and deletion
        isn't modeled as a `Role` method either, since `deleted_at` lives
        only on the ORM row, never on the domain entity (consistent with
        `created_by`/`updated_by` being infrastructure-only across every
        module in this codebase)."""
        ...

    @abstractmethod
    async def assign_to_user(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        role_id: UUID,
        granted_by: UUID | None,
        granted_at: datetime,
    ) -> None:
        """Create the `user_roles` association. Idempotent: assigning a role
        the user already holds is a no-op, not a duplicate-key error —
        callers don't need to check first.
        """
        ...

    @abstractmethod
    async def revoke_from_user(self, *, user_id: UUID, role_id: UUID) -> None: ...

    @abstractmethod
    async def is_assigned_to_user(self, *, user_id: UUID, role_id: UUID) -> bool: ...


class PermissionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, permission_id: UUID) -> Permission | None: ...

    @abstractmethod
    async def get_by_code(self, code: str) -> Permission | None: ...

    @abstractmethod
    async def list_all(self) -> list[Permission]: ...

    @abstractmethod
    async def list_for_role(self, role_id: UUID) -> list[Permission]: ...

    @abstractmethod
    async def add(self, permission: Permission) -> None: ...


class UserSessionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> UserSession | None: ...

    @abstractmethod
    async def list_active_for_user(self, user_id: UUID) -> list[UserSession]: ...

    @abstractmethod
    async def add(self, session: UserSession) -> None: ...


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def get_by_id(self, token_id: UUID) -> RefreshToken | None: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None: ...

    @abstractmethod
    async def list_active_for_session(self, user_session_id: UUID) -> list[RefreshToken]: ...

    @abstractmethod
    async def add(self, token: RefreshToken) -> None: ...
