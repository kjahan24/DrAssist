"""SQLAlchemy ORM models for the Authentication module.

Mirrors `docs/database/01_identity_and_access.md`, with two deliberate
refinements made explicit when this module moved from design to
implementation (see `docs/backend-architecture/03_module_architecture.md`
Authentication section, and the module's `container.py` docstring):

1. `auth_sessions` is renamed `user_sessions` and no longer stores a
   refresh-token hash directly — that's split into its own
   `refresh_tokens` table (below), enabling proper rotation with reuse
   detection (a `UserSession` accumulates a history of `RefreshToken`
   rows over its lifetime, each replacing the last).
2. `organization_id` columns are present but **without** a foreign-key
   constraint to `organizations`, since the Organization module has not
   been implemented yet. The constraint is deferred to a later migration
   once that table exists — the standard expand pattern from
   `docs/database/08_migration_strategy.md §6`, not an oversight.

`auth_password_reset_tokens`, `auth_email_verification_tokens`, and
`auth_login_attempts` from the original design are intentionally **not**
included here — this task scopes the module to exactly the five entities
requested (User, Role, Permission, UserSession, RefreshToken); those three
tables belong to a follow-up task that adds the login/register flows
which actually need them.

**RBAC extension** — a later task ("Implement the RBAC (Roles &
Permissions) module") found `Role`/`Permission`/`RolePermission`/
`UserRole` already fully present here and, rather than forking a second,
disconnected permission system under a new `app.modules.rbac` package,
extended these in place (see `alembic/versions/`'s own migration for the
`ALTER`s this required, and `app.modules.authentication.container`'s
scope note for the full list of what that task added): `RoleModel`
gained `is_active`; `PermissionModel`'s `module` column was renamed to
`resource` (an exact rename, not a new parallel column — `module` and
`resource` are the same concept, so keeping both would only add
confusing, redundant schema) and gained `name`/`action`; `description`
became nullable, matching that task's own field spec.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, INET
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SAEnum

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.modules.authentication.domain.enums import UserStatus

_user_status_enum = SAEnum(
    UserStatus,
    name="user_status_enum",
    create_type=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[UserStatus] = mapped_column(
        _user_status_enum, nullable=False, default=UserStatus.INVITED
    )
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(Text, default=None)
    email_verified_at: Mapped[datetime | None] = mapped_column(default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)
    failed_login_attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(default=None)
    timezone: Mapped[str | None] = mapped_column(Text, default=None)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="en-US")

    __table_args__ = (
        Index(
            "uq_users_organization_id_email",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_status", "organization_id", "status"),
        # `name=` here is the *bare* constraint-name token, not the full
        # constraint name — the "ck" naming convention below (which
        # includes `%(constraint_name)s`) synthesizes the full
        # `ck_users_failed_login_attempts_nonneg` from it. Passing the
        # already-fully-qualified name here would make the convention
        # apply *again* on top of it (`ck_users_ck_users_...`) — see
        # the migration's matching comment for the concrete bug this was.
        CheckConstraint("failed_login_attempts >= 0", name="failed_login_attempts_nonneg"),
    )


class RoleModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "roles"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index(
            "uq_roles_system_name",
            "name",
            unique=True,
            postgresql_where=text("organization_id IS NULL AND deleted_at IS NULL"),
        ),
        Index(
            "uq_roles_org_name",
            "organization_id",
            "name",
            unique=True,
            postgresql_where=text("organization_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("ix_roles_organization_id", "organization_id"),
    )


class PermissionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    resource: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_permissions_code", "code", unique=True, postgresql_where=text("deleted_at IS NULL")
        ),
        Index("ix_permissions_resource_action", "resource", "action"),
    )


class RolePermissionModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("uq_role_permissions_role_permission", "role_id", "permission_id", unique=True),
        Index("ix_role_permissions_permission_id", "permission_id"),
    )


class UserRoleModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "user_roles"

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    granted_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("uq_user_roles_user_role", "user_id", "role_id", unique=True),
        Index("ix_user_roles_organization_id", "organization_id"),
        Index("ix_user_roles_role_id", "role_id"),
    )


class UserSessionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "user_sessions"

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_label: Mapped[str | None] = mapped_column(Text, default=None)
    ip_address: Mapped[str | None] = mapped_column(INET, default=None)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_reason: Mapped[str | None] = mapped_column(Text, default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_organization_id", "organization_id"),
    )


class RefreshTokenModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "refresh_tokens"

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(default=None)
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), default=None
    )
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_reason: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index("uq_refresh_tokens_token_hash", "token_hash", unique=True),
        Index("ix_refresh_tokens_user_session_id", "user_session_id"),
    )
