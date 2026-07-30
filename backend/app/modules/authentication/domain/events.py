"""Domain events published by Authentication module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`. Other modules
subscribe to these without this module ever importing them.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: UUID
    organization_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class UserActivated(DomainEvent):
    user_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserLoginSucceeded(DomainEvent):
    user_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserLoginFailed(DomainEvent):
    user_id: UUID
    organization_id: UUID
    failed_attempt_count: int


@dataclass(frozen=True, kw_only=True)
class UserLocked(DomainEvent):
    user_id: UUID
    organization_id: UUID
    locked_until: str


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(DomainEvent):
    user_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class PasswordChanged(DomainEvent):
    user_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class RoleCreated(DomainEvent):
    role_id: UUID
    organization_id: UUID | None
    name: str


@dataclass(frozen=True, kw_only=True)
class RoleActivated(DomainEvent):
    role_id: UUID


@dataclass(frozen=True, kw_only=True)
class RoleDeactivated(DomainEvent):
    role_id: UUID


@dataclass(frozen=True, kw_only=True)
class RoleDeleted(DomainEvent):
    """Fired directly by the `DeleteRole` use case, not via
    `Role.record_event()` — soft-deletion is a repository-level flag flip
    (see `RoleRepository.delete`), the same "no in-memory aggregate
    mutation" shape `AssignRoleToUser` already uses for `UserRoleAssigned`
    (the `user_roles` association row isn't a full aggregate either)."""

    role_id: UUID
    organization_id: UUID | None


@dataclass(frozen=True, kw_only=True)
class PermissionCreated(DomainEvent):
    permission_id: UUID
    code: str


@dataclass(frozen=True, kw_only=True)
class PermissionGrantedToRole(DomainEvent):
    role_id: UUID
    permission_id: UUID


@dataclass(frozen=True, kw_only=True)
class PermissionRevokedFromRole(DomainEvent):
    role_id: UUID
    permission_id: UUID


@dataclass(frozen=True, kw_only=True)
class UserRoleAssigned(DomainEvent):
    user_id: UUID
    organization_id: UUID
    role_id: UUID
    granted_by: UUID | None


@dataclass(frozen=True, kw_only=True)
class UserRoleRevoked(DomainEvent):
    user_id: UUID
    organization_id: UUID
    role_id: UUID


@dataclass(frozen=True, kw_only=True)
class SessionCreated(DomainEvent):
    session_id: UUID
    user_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class SessionRevoked(DomainEvent):
    session_id: UUID
    user_id: UUID
    organization_id: UUID
    reason: str


@dataclass(frozen=True, kw_only=True)
class RefreshTokenIssued(DomainEvent):
    token_id: UUID
    user_session_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class RefreshTokenRotated(DomainEvent):
    old_token_id: UUID
    new_token_id: UUID
    user_session_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class RefreshTokenRevoked(DomainEvent):
    token_id: UUID
    user_session_id: UUID
    organization_id: UUID
    reason: str


@dataclass(frozen=True, kw_only=True)
class RefreshTokenReuseDetected(DomainEvent):
    """A revoked/already-rotated refresh token was presented again — a
    strong signal of token theft. Security-critical: Notification and
    Audit both subscribe to this for alerting, distinct from routine
    `RefreshTokenRevoked`.
    """

    token_id: UUID
    user_session_id: UUID
    organization_id: UUID
    user_id: UUID
