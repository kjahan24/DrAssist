"""Authentication module aggregate roots: User, Role, Permission, UserSession,
RefreshToken.

Each aggregate reference to another aggregate is by ID only (never an
object reference) — see the aggregate-reference rule in
`docs/backend-architecture/03_module_architecture.md`. All mutation goes
through named methods that enforce the aggregate's invariants and record
domain events; nothing here performs I/O.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.domain.events import (
    PasswordChanged,
    PermissionCreated,
    PermissionGrantedToRole,
    PermissionRevokedFromRole,
    RefreshTokenIssued,
    RefreshTokenRevoked,
    RefreshTokenRotated,
    RoleActivated,
    RoleCreated,
    RoleDeactivated,
    SessionCreated,
    SessionRevoked,
    UserActivated,
    UserDeactivated,
    UserLocked,
    UserLoginFailed,
    UserLoginSucceeded,
    UserRegistered,
)
from app.modules.authentication.domain.exceptions import (
    InvalidRoleOrganizationScopeError,
    PermissionNameRequiredError,
    RefreshTokenAlreadyUsedError,
    RefreshTokenExpiredError,
    RoleNameRequiredError,
    SystemRoleImmutableError,
)
from app.modules.authentication.domain.value_objects import HashedPassword, PermissionCode
from app.shared.domain.common_value_objects import EmailAddress
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class User(AggregateRoot):
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)

    organization_id: UUID
    email: EmailAddress
    password_hash: HashedPassword
    first_name: str
    last_name: str
    phone: str | None = None
    status: UserStatus = UserStatus.INVITED
    mfa_enabled: bool = False
    mfa_secret_encrypted: str | None = None
    email_verified_at: datetime | None = None
    last_login_at: datetime | None = None
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    timezone: str | None = None
    locale: str = "en-US"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @classmethod
    def register(
        cls,
        *,
        organization_id: UUID,
        email: EmailAddress,
        password_hash: HashedPassword,
        first_name: str,
        last_name: str,
        phone: str | None = None,
        locale: str = "en-US",
        timezone: str | None = None,
    ) -> "User":
        user = cls(
            organization_id=organization_id,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            locale=locale,
            timezone=timezone,
        )
        user.record_event(
            UserRegistered(user_id=user.id, organization_id=organization_id, email=str(email))
        )
        return user

    def activate(self) -> None:
        self.status = UserStatus.ACTIVE
        self.touch()
        self.record_event(UserActivated(user_id=self.id, organization_id=self.organization_id))

    def deactivate(self) -> None:
        self.status = UserStatus.DEACTIVATED
        self.touch()
        self.record_event(UserDeactivated(user_id=self.id, organization_id=self.organization_id))

    def suspend(self) -> None:
        self.status = UserStatus.SUSPENDED
        self.touch()

    def change_password(self, new_password_hash: HashedPassword) -> None:
        self.password_hash = new_password_hash
        self.touch()
        self.record_event(PasswordChanged(user_id=self.id, organization_id=self.organization_id))

    def verify_email(self, *, now: datetime) -> None:
        self.email_verified_at = now
        self.touch()

    def is_locked(self, *, now: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > now

    def can_authenticate(self, *, now: datetime) -> bool:
        return self.status is UserStatus.ACTIVE and not self.is_locked(now=now)

    def record_login_success(self, *, now: datetime) -> None:
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = now
        self.touch()
        self.record_event(UserLoginSucceeded(user_id=self.id, organization_id=self.organization_id))

    def record_login_failure(self, *, now: datetime) -> None:
        self.failed_login_attempts += 1
        self.touch()
        self.record_event(
            UserLoginFailed(
                user_id=self.id,
                organization_id=self.organization_id,
                failed_attempt_count=self.failed_login_attempts,
            )
        )
        if self.failed_login_attempts >= self.MAX_FAILED_LOGIN_ATTEMPTS:
            self.locked_until = now + self.LOCKOUT_DURATION
            self.record_event(
                UserLocked(
                    user_id=self.id,
                    organization_id=self.organization_id,
                    locked_until=self.locked_until.isoformat(),
                )
            )


@dataclass(kw_only=True, eq=False)
class Role(AggregateRoot):
    """`organization_id`/`is_system_role` are cross-validated in
    `__post_init__`, not left as two independently-set fields that could
    drift into an invalid combination: "Global system roles must have
    organization_id = NULL" and "Organization roles must belong to
    exactly one organization" are two halves of one invariant, enforced
    unconditionally (applies to every construction path, including
    `role_to_domain` reconstructing a `Role` from a database row, not
    just `create()` — the same universal-`__post_init__` convention every
    other module's aggregates use for their own construction invariants).

    `is_active` defaults `True` — a role is usable the moment it's
    created; deactivation is a separate, explicit step via `deactivate()`.
    """

    organization_id: UUID | None
    name: str
    description: str | None = None
    is_system_role: bool = False
    is_active: bool = True
    permission_ids: set[UUID] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise RoleNameRequiredError()
        self.name = self.name.strip()

        if self.is_system_role and self.organization_id is not None:
            raise InvalidRoleOrganizationScopeError(
                is_system_role=True, organization_id=self.organization_id
            )
        if not self.is_system_role and self.organization_id is None:
            raise InvalidRoleOrganizationScopeError(is_system_role=False, organization_id=None)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID | None,
        name: str,
        description: str | None = None,
        is_system_role: bool = False,
    ) -> "Role":
        role = cls(
            organization_id=organization_id,
            name=name,
            description=description,
            is_system_role=is_system_role,
        )
        role.record_event(RoleCreated(role_id=role.id, organization_id=organization_id, name=name))
        return role

    def has_permission(self, permission_id: UUID) -> bool:
        return permission_id in self.permission_ids

    def grant_permission(self, permission_id: UUID) -> None:
        if self.is_system_role:
            raise SystemRoleImmutableError(self.id)
        if permission_id in self.permission_ids:
            return
        self.permission_ids.add(permission_id)
        self.touch()
        self.record_event(PermissionGrantedToRole(role_id=self.id, permission_id=permission_id))

    def revoke_permission(self, permission_id: UUID) -> None:
        if self.is_system_role:
            raise SystemRoleImmutableError(self.id)
        if permission_id not in self.permission_ids:
            return
        self.permission_ids.discard(permission_id)
        self.touch()
        self.record_event(PermissionRevokedFromRole(role_id=self.id, permission_id=permission_id))

    def activate(self) -> None:
        """Blocked for system roles — same "cannot be modified" guard as
        `grant_permission`/`revoke_permission`; a system role is always
        active and is never expected to need reactivating."""
        if self.is_system_role:
            raise SystemRoleImmutableError(self.id)
        if self.is_active:
            return
        self.is_active = True
        self.touch()
        self.record_event(RoleActivated(role_id=self.id))

    def deactivate(self) -> None:
        """Blocked for system roles — deactivating one would silently
        strip permissions from every user who holds it, which "system
        roles cannot be modified" is precisely meant to prevent."""
        if self.is_system_role:
            raise SystemRoleImmutableError(self.id)
        if not self.is_active:
            return
        self.is_active = False
        self.touch()
        self.record_event(RoleDeactivated(role_id=self.id))


@dataclass(kw_only=True, eq=False)
class Permission(AggregateRoot):
    """`resource`/`action` are *derived* from `code` at construction time
    (`code`'s own `resource.action` format — see
    `domain.value_objects.PermissionCode` — already carries this
    information), not independently caller-supplied: storing them as
    plain columns (rather than parsing `code` on every read) is what lets
    a future admin UI/FHIR mapping filter or index on them directly, but
    deriving rather than accepting them as separate constructor arguments
    means they can never drift out of sync with `code` — `code` remains
    the single source of truth. `description` is nullable ("no format was
    specified" — the same reasoning already applied to `reason_for_visit`/
    `notes`-shaped free-text fields elsewhere in this codebase); `name` is
    required, matching `Role.name`'s own required-non-blank treatment.
    """

    code: PermissionCode
    name: str
    resource: str
    action: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise PermissionNameRequiredError()
        self.name = self.name.strip()

    @classmethod
    def create(
        cls, *, code: PermissionCode, name: str, description: str | None = None
    ) -> "Permission":
        resource, action = code.value.split(".", 1)
        permission = cls(
            code=code, name=name, resource=resource, action=action, description=description
        )
        permission.record_event(PermissionCreated(permission_id=permission.id, code=str(code)))
        return permission


@dataclass(kw_only=True, eq=False)
class UserSession(AggregateRoot):
    organization_id: UUID
    user_id: UUID
    issued_at: datetime
    expires_at: datetime
    device_label: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    last_used_at: datetime | None = None

    @classmethod
    def start(
        cls,
        *,
        organization_id: UUID,
        user_id: UUID,
        expires_at: datetime,
        now: datetime,
        device_label: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> "UserSession":
        session = cls(
            organization_id=organization_id,
            user_id=user_id,
            issued_at=now,
            expires_at=expires_at,
            device_label=device_label,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.record_event(
            SessionCreated(session_id=session.id, user_id=user_id, organization_id=organization_id)
        )
        return session

    def is_active(self, *, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now

    def mark_used(self, *, now: datetime) -> None:
        self.last_used_at = now
        self.touch()

    def revoke(self, *, reason: str, now: datetime) -> None:
        if self.revoked_at is not None:
            return
        self.revoked_at = now
        self.revoked_reason = reason
        self.touch()
        self.record_event(
            SessionRevoked(
                session_id=self.id,
                user_id=self.user_id,
                organization_id=self.organization_id,
                reason=reason,
            )
        )


@dataclass(kw_only=True, eq=False)
class RefreshToken(AggregateRoot):
    organization_id: UUID
    user_session_id: UUID
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    used_at: datetime | None = None
    replaced_by_token_id: UUID | None = None
    revoked_at: datetime | None = None
    revoked_reason: str | None = None

    @classmethod
    def issue(
        cls,
        *,
        organization_id: UUID,
        user_session_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> "RefreshToken":
        token = cls(
            organization_id=organization_id,
            user_session_id=user_session_id,
            token_hash=token_hash,
            issued_at=now,
            expires_at=expires_at,
        )
        token.record_event(
            RefreshTokenIssued(
                token_id=token.id,
                user_session_id=user_session_id,
                organization_id=organization_id,
            )
        )
        return token

    def is_active(self, *, now: datetime) -> bool:
        return self.used_at is None and self.revoked_at is None and self.expires_at > now

    def rotate(self, *, new_token_id: UUID, now: datetime) -> None:
        """Consume this token, linking it to its replacement.

        Raises `RefreshTokenAlreadyUsedError` if this token was already
        rotated or revoked — the caller (the future token-refresh use
        case) must treat that as a reuse-detection signal and revoke the
        owning `UserSession` entirely, which this method deliberately does
        not do itself: reaching into another aggregate would cross the
        aggregate boundary (see module docstring).
        """
        if self.used_at is not None or self.revoked_at is not None:
            raise RefreshTokenAlreadyUsedError(self.id)
        if now >= self.expires_at:
            raise RefreshTokenExpiredError(self.id)
        self.used_at = now
        self.replaced_by_token_id = new_token_id
        self.touch()
        self.record_event(
            RefreshTokenRotated(
                old_token_id=self.id,
                new_token_id=new_token_id,
                user_session_id=self.user_session_id,
                organization_id=self.organization_id,
            )
        )

    def revoke(self, *, reason: str, now: datetime) -> None:
        if self.revoked_at is not None:
            return
        self.revoked_at = now
        self.revoked_reason = reason
        self.touch()
        self.record_event(
            RefreshTokenRevoked(
                token_id=self.id,
                user_session_id=self.user_session_id,
                organization_id=self.organization_id,
                reason=reason,
            )
        )
