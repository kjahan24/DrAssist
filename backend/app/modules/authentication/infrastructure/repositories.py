"""Concrete SQLAlchemy repository implementations.

Every `add()` below is "upsert": look up the row by id, create it if
missing, then overwrite its mapped columns from the domain entity's
current in-memory state. This is what lets the domain-vs-ORM object split
work without a separate `update()` method on the interface (see
`docs/backend-architecture/04_repository_and_service_patterns.md`) — a
use case mutates the aggregate it got from `get_by_id`, calls `add()`
again, and the Unit of Work's `commit()` persists the diff.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.modules.authentication.infrastructure.mappers import (
    apply_permission_to_model,
    apply_refresh_token_to_model,
    apply_role_to_model,
    apply_user_session_to_model,
    apply_user_to_model,
    permission_to_domain,
    refresh_token_to_domain,
    role_to_domain,
    user_session_to_domain,
    user_to_domain,
)
from app.modules.authentication.infrastructure.models import (
    PermissionModel,
    RefreshTokenModel,
    RoleModel,
    RolePermissionModel,
    UserModel,
    UserRoleModel,
    UserSessionModel,
)
from app.shared.domain.common_value_objects import EmailAddress


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        if model is None or model.deleted_at is not None:
            return None
        return user_to_domain(model)

    async def get_by_email(self, *, organization_id: UUID, email: EmailAddress) -> User | None:
        stmt = select(UserModel).where(
            UserModel.organization_id == organization_id,
            UserModel.email == str(email),
            UserModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return user_to_domain(model) if model is not None else None

    async def list_by_organization(
        self, *, organization_id: UUID, offset: int = 0, limit: int = 20
    ) -> list[User]:
        stmt = (
            select(UserModel)
            .where(UserModel.organization_id == organization_id, UserModel.deleted_at.is_(None))
            .order_by(UserModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [user_to_domain(model) for model in models]

    async def add(self, user: User) -> None:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            model = UserModel()
            self._session.add(model)
        apply_user_to_model(user, model)


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_permission_ids(self, role_id: UUID) -> set[UUID]:
        stmt = select(RolePermissionModel.permission_id).where(
            RolePermissionModel.role_id == role_id,
            RolePermissionModel.deleted_at.is_(None),
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def get_by_id(self, role_id: UUID) -> Role | None:
        model = await self._session.get(RoleModel, role_id)
        if model is None or model.deleted_at is not None:
            return None
        return role_to_domain(model, await self._get_permission_ids(role_id))

    async def get_system_role_by_name(self, name: str) -> Role | None:
        stmt = select(RoleModel).where(
            RoleModel.organization_id.is_(None),
            RoleModel.name == name,
            RoleModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return role_to_domain(model, await self._get_permission_ids(model.id))

    async def get_org_role_by_name(self, *, organization_id: UUID, name: str) -> Role | None:
        stmt = select(RoleModel).where(
            RoleModel.organization_id == organization_id,
            RoleModel.name == name,
            RoleModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        return role_to_domain(model, await self._get_permission_ids(model.id))

    async def list_for_user(self, user_id: UUID) -> list[Role]:
        stmt = (
            select(RoleModel)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.deleted_at.is_(None),
                RoleModel.deleted_at.is_(None),
            )
        )
        models = (await self._session.execute(stmt)).scalars().all()
        roles = []
        for model in models:
            roles.append(role_to_domain(model, await self._get_permission_ids(model.id)))
        return roles

    async def list_by_organization(self, organization_id: UUID) -> list[Role]:
        stmt = (
            select(RoleModel)
            .where(RoleModel.organization_id == organization_id, RoleModel.deleted_at.is_(None))
            .order_by(RoleModel.name)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [role_to_domain(model, await self._get_permission_ids(model.id)) for model in models]

    async def list_system_roles(self) -> list[Role]:
        stmt = (
            select(RoleModel)
            .where(RoleModel.organization_id.is_(None), RoleModel.deleted_at.is_(None))
            .order_by(RoleModel.name)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [role_to_domain(model, await self._get_permission_ids(model.id)) for model in models]

    async def add(self, role: Role) -> None:
        model = await self._session.get(RoleModel, role.id)
        if model is None:
            model = RoleModel()
            self._session.add(model)
        apply_role_to_model(role, model)

        existing_stmt = select(RolePermissionModel).where(
            RolePermissionModel.role_id == role.id,
            RolePermissionModel.deleted_at.is_(None),
        )
        existing_rows = (await self._session.execute(existing_stmt)).scalars().all()
        existing_permission_ids = {row.permission_id for row in existing_rows}

        now = datetime.now(UTC)
        for row in existing_rows:
            if row.permission_id not in role.permission_ids:
                row.deleted_at = now

        for permission_id in role.permission_ids - existing_permission_ids:
            self._session.add(RolePermissionModel(role_id=role.id, permission_id=permission_id))

    async def assign_to_user(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        role_id: UUID,
        granted_by: UUID | None,
        granted_at: datetime,
    ) -> None:
        stmt = select(UserRoleModel).where(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_id == role_id,
            UserRoleModel.deleted_at.is_(None),
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return
        self._session.add(
            UserRoleModel(
                organization_id=organization_id,
                user_id=user_id,
                role_id=role_id,
                granted_by=granted_by,
                granted_at=granted_at,
            )
        )

    async def revoke_from_user(self, *, user_id: UUID, role_id: UUID) -> None:
        stmt = select(UserRoleModel).where(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_id == role_id,
            UserRoleModel.deleted_at.is_(None),
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is not None:
            row.deleted_at = datetime.now(UTC)

    async def delete(self, role_id: UUID) -> None:
        model = await self._session.get(RoleModel, role_id)
        if model is not None and model.deleted_at is None:
            model.deleted_at = datetime.now(UTC)

    async def is_assigned_to_user(self, *, user_id: UUID, role_id: UUID) -> bool:
        stmt = select(UserRoleModel.id).where(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_id == role_id,
            UserRoleModel.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None


class SqlAlchemyPermissionRepository(PermissionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        model = await self._session.get(PermissionModel, permission_id)
        if model is None or model.deleted_at is not None:
            return None
        return permission_to_domain(model)

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(PermissionModel).where(
            PermissionModel.code == code, PermissionModel.deleted_at.is_(None)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return permission_to_domain(model) if model is not None else None

    async def list_all(self) -> list[Permission]:
        stmt = (
            select(PermissionModel)
            .where(PermissionModel.deleted_at.is_(None))
            .order_by(PermissionModel.resource, PermissionModel.code)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [permission_to_domain(model) for model in models]

    async def list_for_role(self, role_id: UUID) -> list[Permission]:
        stmt = (
            select(PermissionModel)
            .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
            .where(
                RolePermissionModel.role_id == role_id,
                RolePermissionModel.deleted_at.is_(None),
                PermissionModel.deleted_at.is_(None),
            )
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [permission_to_domain(model) for model in models]

    async def add(self, permission: Permission) -> None:
        model = await self._session.get(PermissionModel, permission.id)
        if model is None:
            model = PermissionModel()
            self._session.add(model)
        apply_permission_to_model(permission, model)


class SqlAlchemyUserSessionRepository(UserSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        model = await self._session.get(UserSessionModel, session_id)
        if model is None or model.deleted_at is not None:
            return None
        return user_session_to_domain(model)

    async def list_active_for_user(self, user_id: UUID) -> list[UserSession]:
        now = datetime.now(UTC)
        stmt = select(UserSessionModel).where(
            UserSessionModel.user_id == user_id,
            UserSessionModel.revoked_at.is_(None),
            UserSessionModel.expires_at > now,
            UserSessionModel.deleted_at.is_(None),
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [user_session_to_domain(model) for model in models]

    async def add(self, session: UserSession) -> None:
        model = await self._session.get(UserSessionModel, session.id)
        if model is None:
            model = UserSessionModel()
            self._session.add(model)
        apply_user_session_to_model(session, model)


class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, token_id: UUID) -> RefreshToken | None:
        model = await self._session.get(RefreshTokenModel, token_id)
        if model is None or model.deleted_at is not None:
            return None
        return refresh_token_to_domain(model)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash,
            RefreshTokenModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return refresh_token_to_domain(model) if model is not None else None

    async def list_active_for_session(self, user_session_id: UUID) -> list[RefreshToken]:
        now = datetime.now(UTC)
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.user_session_id == user_session_id,
            RefreshTokenModel.used_at.is_(None),
            RefreshTokenModel.revoked_at.is_(None),
            RefreshTokenModel.expires_at > now,
            RefreshTokenModel.deleted_at.is_(None),
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [refresh_token_to_domain(model) for model in models]

    async def add(self, token: RefreshToken) -> None:
        model = await self._session.get(RefreshTokenModel, token.id)
        if model is None:
            model = RefreshTokenModel()
            self._session.add(model)
        apply_refresh_token_to_model(token, model)
