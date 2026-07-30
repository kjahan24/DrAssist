"""Data Transfer Objects for the Authentication module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; the two DTOs at the
bottom (`UserSummaryDTO`, `AuthenticatedPrincipalDTO`) are also the ones
re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.authentication.domain.enums import UserStatus

# --- CreateRole -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateRoleInput:
    organization_id: UUID | None
    name: str
    description: str | None = None
    is_system_role: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateRoleOutput:
    role_id: UUID
    organization_id: UUID | None
    name: str


# --- AssignPermissionToRole --------------------------------------------


@dataclass(frozen=True, slots=True)
class AssignPermissionToRoleInput:
    role_id: UUID
    permission_code: str
    granted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AssignPermissionToRoleOutput:
    role_id: UUID
    permission_id: UUID
    permission_code: str


# --- AssignRoleToUser ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class AssignRoleToUserInput:
    organization_id: UUID
    user_id: UUID
    role_id: UUID
    granted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AssignRoleToUserOutput:
    user_id: UUID
    role_id: UUID


# --- DeleteRole / ActivateRole / DeactivateRole -------------------------


@dataclass(frozen=True, slots=True)
class DeleteRoleInput:
    role_id: UUID


@dataclass(frozen=True, slots=True)
class DeleteRoleOutput:
    role_id: UUID


@dataclass(frozen=True, slots=True)
class ActivateRoleInput:
    role_id: UUID


@dataclass(frozen=True, slots=True)
class DeactivateRoleInput:
    role_id: UUID


@dataclass(frozen=True, slots=True)
class RoleStatusOutput:
    role_id: UUID
    is_active: bool


# --- CreatePermission -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreatePermissionInput:
    code: str
    name: str
    description: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreatePermissionOutput:
    permission_id: UUID
    code: str
    resource: str
    action: str


# --- Cross-cutting read models (also re-exported via public/dto.py) ----


@dataclass(frozen=True, slots=True)
class RoleSummaryDTO:
    role_id: UUID
    organization_id: UUID | None
    name: str
    description: str | None
    is_system_role: bool
    is_active: bool


@dataclass(frozen=True, slots=True)
class PermissionSummaryDTO:
    permission_id: UUID
    code: str
    name: str
    description: str | None
    resource: str
    action: str


@dataclass(frozen=True, slots=True)
class UserSummaryDTO:
    user_id: UUID
    organization_id: UUID
    email: str
    first_name: str
    last_name: str
    status: UserStatus


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipalDTO:
    """What `get_current_user` resolves a valid access token into. Deliberately
    narrow — a route handler gets identity and effective permissions, never
    the full mutable `User` aggregate.
    """

    user_id: UUID
    organization_id: UUID
    session_id: UUID
    email: str
    permissions: frozenset[str]
