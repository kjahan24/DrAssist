"""In-memory test doubles for the Authentication module's repositories and
Unit of Work — each implements the exact same interface its real
SQLAlchemy counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case tests depend on these, never
on a real database.
"""

from uuid import UUID

from app.modules.authentication.domain.entities import (
    Permission,
    RefreshToken,
    Role,
    User,
    UserSession,
)
from app.modules.authentication.domain.repositories import (
    PermissionRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
    UserSessionRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.common_value_objects import EmailAddress
from app.shared.domain.domain_event import DomainEvent


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, *, organization_id: UUID, email: EmailAddress) -> User | None:
        for user in self._users.values():
            if user.organization_id == organization_id and user.email == email:
                return user
        return None

    async def list_by_organization(
        self, *, organization_id: UUID, offset: int = 0, limit: int = 20
    ) -> list[User]:
        matches = [u for u in self._users.values() if u.organization_id == organization_id]
        return matches[offset : offset + limit]

    async def add(self, user: User) -> None:
        self._users[user.id] = user


class FakeRoleRepository(RoleRepository):
    def __init__(self) -> None:
        self._roles: dict[UUID, Role] = {}
        self._user_roles: set[tuple[UUID, UUID]] = set()

    async def get_by_id(self, role_id: UUID) -> Role | None:
        return self._roles.get(role_id)

    async def get_system_role_by_name(self, name: str) -> Role | None:
        for role in self._roles.values():
            if role.organization_id is None and role.name == name:
                return role
        return None

    async def get_org_role_by_name(self, *, organization_id: UUID, name: str) -> Role | None:
        for role in self._roles.values():
            if role.organization_id == organization_id and role.name == name:
                return role
        return None

    async def list_for_user(self, user_id: UUID) -> list[Role]:
        role_ids = {role_id for (uid, role_id) in self._user_roles if uid == user_id}
        return [self._roles[rid] for rid in role_ids if rid in self._roles]

    async def add(self, role: Role) -> None:
        self._roles[role.id] = role

    async def assign_to_user(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        role_id: UUID,
        granted_by: UUID | None,
        granted_at: object,
    ) -> None:
        self._user_roles.add((user_id, role_id))

    async def revoke_from_user(self, *, user_id: UUID, role_id: UUID) -> None:
        self._user_roles.discard((user_id, role_id))

    async def is_assigned_to_user(self, *, user_id: UUID, role_id: UUID) -> bool:
        return (user_id, role_id) in self._user_roles


class FakePermissionRepository(PermissionRepository):
    """`list_for_role` is backed by its own association map, independent of
    `FakeRoleRepository`'s `Role.permission_ids` — exactly like the real
    implementation, where `role_permissions` is a separate table from
    `roles`. Tests that exercise a full grant flow (`AssignPermissionToRole`)
    only assert on the `Role` aggregate's own state; tests of
    `RbacPermissionService` (which reads through this repository) seed
    this map directly via `seed_role_permission`.
    """

    def __init__(self) -> None:
        self._permissions: dict[UUID, Permission] = {}
        self._role_permission_ids: dict[UUID, set[UUID]] = {}

    def seed_role_permission(self, role_id: UUID, permission_id: UUID) -> None:
        self._role_permission_ids.setdefault(role_id, set()).add(permission_id)

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        return self._permissions.get(permission_id)

    async def get_by_code(self, code: str) -> Permission | None:
        for permission in self._permissions.values():
            if str(permission.code) == code:
                return permission
        return None

    async def list_all(self) -> list[Permission]:
        return list(self._permissions.values())

    async def list_for_role(self, role_id: UUID) -> list[Permission]:
        ids = self._role_permission_ids.get(role_id, set())
        return [self._permissions[pid] for pid in ids if pid in self._permissions]

    async def add(self, permission: Permission) -> None:
        self._permissions[permission.id] = permission


class FakeUserSessionRepository(UserSessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[UUID, UserSession] = {}

    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        return self._sessions.get(session_id)

    async def list_active_for_user(self, user_id: UUID) -> list[UserSession]:
        return [s for s in self._sessions.values() if s.user_id == user_id]

    async def add(self, session: UserSession) -> None:
        self._sessions[session.id] = session


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self) -> None:
        self._tokens: dict[UUID, RefreshToken] = {}

    async def get_by_id(self, token_id: UUID) -> RefreshToken | None:
        return self._tokens.get(token_id)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        for token in self._tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    async def list_active_for_session(self, user_session_id: UUID) -> list[RefreshToken]:
        return [t for t in self._tokens.values() if t.user_session_id == user_session_id]

    async def add(self, token: RefreshToken) -> None:
        self._tokens[token.id] = token


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass
