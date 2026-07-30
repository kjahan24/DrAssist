"""Domain exceptions for the Authentication module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. HTTP
translation is deferred to the future API layer that will call the
use cases raising these (the login/register flows this task explicitly
excludes).
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class DuplicateEmailError(DomainError):
    def __init__(self, email: str) -> None:
        super().__init__(f"a user with email {email!r} already exists in this organization")
        self.email = email


class UserNotFoundError(DomainError):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"no user found with id {user_id}")
        self.user_id = user_id


class AccountLockedError(DomainError):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"user {user_id} is locked out due to repeated failed login attempts")
        self.user_id = user_id


class InactiveAccountError(DomainError):
    def __init__(self, user_id: UUID, status: str) -> None:
        super().__init__(f"user {user_id} cannot authenticate while status is {status!r}")
        self.user_id = user_id
        self.status = status


class DuplicateRoleNameError(DomainError):
    def __init__(self, name: str) -> None:
        super().__init__(f"a role named {name!r} already exists in this scope")
        self.name = name


class RoleNotFoundError(DomainError):
    def __init__(self, role_id: UUID) -> None:
        super().__init__(f"no role found with id {role_id}")
        self.role_id = role_id


class SystemRoleImmutableError(DomainError):
    def __init__(self, role_id: UUID) -> None:
        super().__init__(f"role {role_id} is a system-defined role and cannot be modified")
        self.role_id = role_id


class RoleNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("role name must not be blank")


class InvalidRoleOrganizationScopeError(DomainError):
    """ "Global system roles must have organization_id = NULL" and
    "Organization roles must belong to exactly one organization" — the
    two halves of the same invariant, both violations reported by this
    one exception."""

    def __init__(self, *, is_system_role: bool, organization_id: UUID | None) -> None:
        if is_system_role:
            super().__init__(
                f"system role has organization_id={organization_id}, but system roles must "
                "have organization_id=NULL"
            )
        else:
            super().__init__(
                "organization-scoped role has organization_id=NULL, but every non-system role "
                "must belong to exactly one organization"
            )
        self.is_system_role = is_system_role
        self.organization_id = organization_id


class InactiveRoleError(DomainError):
    def __init__(self, role_id: UUID) -> None:
        super().__init__(f"role {role_id} is inactive and cannot be assigned")
        self.role_id = role_id


class RoleOrganizationMismatchError(DomainError):
    def __init__(self, role_id: UUID, organization_id: UUID) -> None:
        super().__init__(f"role {role_id} does not belong to organization {organization_id}")
        self.role_id = role_id
        self.organization_id = organization_id


class PermissionNotFoundError(DomainError):
    def __init__(self, permission_id: UUID) -> None:
        super().__init__(f"no permission found with id {permission_id}")
        self.permission_id = permission_id


class PermissionNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("permission name must not be blank")


class InvalidPermissionCodeError(DomainError):
    def __init__(self, code: str) -> None:
        super().__init__(f"{code!r} is not a valid permission code (expected 'resource.action')")
        self.code = code


class PermissionCodeNotRegisteredError(DomainError):
    """The code is well-formed but no `Permission` with it is registered."""

    def __init__(self, code: str) -> None:
        super().__init__(f"no registered permission has code {code!r}")
        self.code = code


class DuplicatePermissionCodeError(DomainError):
    def __init__(self, code: str) -> None:
        super().__init__(f"a permission with code {code!r} already exists")
        self.code = code


class SessionNotFoundError(DomainError):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"no session found with id {session_id}")
        self.session_id = session_id


class SessionRevokedError(DomainError):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"session {session_id} has been revoked")
        self.session_id = session_id


class SessionExpiredError(DomainError):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"session {session_id} has expired")
        self.session_id = session_id


class RefreshTokenNotFoundError(DomainError):
    def __init__(self, token_id: UUID) -> None:
        super().__init__(f"no refresh token found with id {token_id}")
        self.token_id = token_id


class RefreshTokenExpiredError(DomainError):
    def __init__(self, token_id: UUID) -> None:
        super().__init__(f"refresh token {token_id} has expired")
        self.token_id = token_id


class RefreshTokenAlreadyUsedError(DomainError):
    """Raised when a refresh token that was already rotated/revoked is presented
    again — a strong signal of token theft (reuse detection). The caller
    (a future `RefreshAccessToken` use case) is expected to respond by
    revoking the entire session, not just rejecting this one request.
    """

    def __init__(self, token_id: UUID) -> None:
        super().__init__(f"refresh token {token_id} has already been used or revoked")
        self.token_id = token_id
