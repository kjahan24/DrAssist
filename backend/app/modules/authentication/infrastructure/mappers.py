"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
`Role`'s `permission_ids` isn't a column on `RoleModel` — it's derived
from `role_permissions`, so `role_to_domain` takes it as a separate
argument; the repository is responsible for fetching it.
"""

from uuid import UUID

from app.modules.authentication.domain.entities import (
    Permission,
    RefreshToken,
    Role,
    User,
    UserSession,
)
from app.modules.authentication.domain.value_objects import HashedPassword, PermissionCode
from app.modules.authentication.infrastructure.models import (
    PermissionModel,
    RefreshTokenModel,
    RoleModel,
    UserModel,
    UserSessionModel,
)
from app.shared.domain.common_value_objects import EmailAddress

# --- User ----------------------------------------------------------------


def user_to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        organization_id=model.organization_id,
        email=EmailAddress(model.email),
        password_hash=HashedPassword(model.password_hash),
        first_name=model.first_name,
        last_name=model.last_name,
        phone=model.phone,
        status=model.status,
        mfa_enabled=model.mfa_enabled,
        mfa_secret_encrypted=model.mfa_secret_encrypted,
        email_verified_at=model.email_verified_at,
        last_login_at=model.last_login_at,
        failed_login_attempts=model.failed_login_attempts,
        locked_until=model.locked_until,
        timezone=model.timezone,
        locale=model.locale,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_user_to_model(entity: User, model: UserModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.email = str(entity.email)
    model.password_hash = entity.password_hash.value
    model.first_name = entity.first_name
    model.last_name = entity.last_name
    model.phone = entity.phone
    model.status = entity.status
    model.mfa_enabled = entity.mfa_enabled
    model.mfa_secret_encrypted = entity.mfa_secret_encrypted
    model.email_verified_at = entity.email_verified_at
    model.last_login_at = entity.last_login_at
    model.failed_login_attempts = entity.failed_login_attempts
    model.locked_until = entity.locked_until
    model.timezone = entity.timezone
    model.locale = entity.locale


# --- Role ------------------------------------------------------------------


def role_to_domain(model: RoleModel, permission_ids: set[UUID]) -> Role:
    return Role(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        is_system_role=model.is_system_role,
        permission_ids=set(permission_ids),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_role_to_model(entity: Role, model: RoleModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.name = entity.name
    model.description = entity.description
    model.is_system_role = entity.is_system_role


# --- Permission --------------------------------------------------------


def permission_to_domain(model: PermissionModel) -> Permission:
    return Permission(
        id=model.id,
        code=PermissionCode(model.code),
        module=model.module,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_permission_to_model(entity: Permission, model: PermissionModel) -> None:
    model.id = entity.id
    model.code = str(entity.code)
    model.module = entity.module
    model.description = entity.description


# --- UserSession -----------------------------------------------------------


def user_session_to_domain(model: UserSessionModel) -> UserSession:
    return UserSession(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        issued_at=model.issued_at,
        expires_at=model.expires_at,
        device_label=model.device_label,
        ip_address=model.ip_address,
        user_agent=model.user_agent,
        revoked_at=model.revoked_at,
        revoked_reason=model.revoked_reason,
        last_used_at=model.last_used_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_user_session_to_model(entity: UserSession, model: UserSessionModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.user_id = entity.user_id
    model.issued_at = entity.issued_at
    model.expires_at = entity.expires_at
    model.device_label = entity.device_label
    model.ip_address = entity.ip_address
    model.user_agent = entity.user_agent
    model.revoked_at = entity.revoked_at
    model.revoked_reason = entity.revoked_reason
    model.last_used_at = entity.last_used_at


# --- RefreshToken ------------------------------------------------------


def refresh_token_to_domain(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        organization_id=model.organization_id,
        user_session_id=model.user_session_id,
        token_hash=model.token_hash,
        issued_at=model.issued_at,
        expires_at=model.expires_at,
        used_at=model.used_at,
        replaced_by_token_id=model.replaced_by_token_id,
        revoked_at=model.revoked_at,
        revoked_reason=model.revoked_reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_refresh_token_to_model(entity: RefreshToken, model: RefreshTokenModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.user_session_id = entity.user_session_id
    model.token_hash = entity.token_hash
    model.issued_at = entity.issued_at
    model.expires_at = entity.expires_at
    model.used_at = entity.used_at
    model.replaced_by_token_id = entity.replaced_by_token_id
    model.revoked_at = entity.revoked_at
    model.revoked_reason = entity.revoked_reason
