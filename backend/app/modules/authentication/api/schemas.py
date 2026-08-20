"""Pydantic v2 request/response schemas for the Authentication module.

`RoleResponse`/`PermissionResponse`/etc. back the RBAC administration
endpoints. `RegisterRequest`/`LoginRequest`/`RegisterResponse`/
`LoginResponse`/`AuthenticatedPrincipalResponse` back the register/login
endpoints — `LoginResponse`'s field names (`access_token`, `principal`)
and `AuthenticatedPrincipalResponse`'s (`user_id`, `organization_id`,
`session_id`, `email`, `permissions`) are load-bearing: they match
`frontend/src/app/(auth)/login/page.tsx`'s own `LoginResponse` TS
interface and `frontend/src/types/index.ts`'s `AuthenticatedPrincipal`
type exactly, field for field.

Schemas never expose a domain entity directly, and never accept
`organization_id`/`status`/other server-controlled fields from the client
— see `docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

import re
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.modules.authentication.domain.enums import UserStatus
from app.schemas.base import ORJSONModel

_PASSWORD_LOWERCASE = re.compile(r"[a-z]")
_PASSWORD_UPPERCASE = re.compile(r"[A-Z]")
_PASSWORD_DIGIT = re.compile(r"[0-9]")


def _validate_password_strength(value: str) -> str:
    """Mirrors `frontend/src/lib/auth/validation.ts`'s `passwordSchema`
    exactly (min length 8, needs one lowercase/uppercase/digit) — client
    and server must agree on the policy, and the server is the one that
    actually enforces it; the frontend copy is only ever a UX head start."""
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not _PASSWORD_LOWERCASE.search(value):
        raise ValueError("Password must include a lowercase letter")
    if not _PASSWORD_UPPERCASE.search(value):
        raise ValueError("Password must include an uppercase letter")
    if not _PASSWORD_DIGIT.search(value):
        raise ValueError("Password must include a number")
    return value


class UserResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None = None
    status: UserStatus
    mfa_enabled: bool
    locale: str


class RoleResponse(ORJSONModel):
    id: UUID
    organization_id: UUID | None
    name: str
    description: str | None = None
    is_system_role: bool
    is_active: bool


class PermissionResponse(ORJSONModel):
    """`name`/`resource`/`action` (nullable `description`) — not the
    original `module`/non-nullable `description` shape this schema had
    before the RBAC-extension turn added `Permission.resource`/`.action`
    as derived, stored columns (see `domain/entities.py`). Fixed here,
    by the REST APIs task, since this is the first turn that actually
    wires this schema to a response body — see `RoleResponse.is_active`
    (added the same way, for the same reason: `Role.is_active` already
    existed on the entity/DTO, this schema just hadn't caught up)."""

    id: UUID
    code: str
    name: str
    resource: str
    action: str
    description: str | None = None


class CreateRoleRequest(ORJSONModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class CreatePermissionRequest(ORJSONModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class AssignPermissionToRoleRequest(ORJSONModel):
    permission_code: str = Field(min_length=1, max_length=100)


class AssignRoleToUserRequest(ORJSONModel):
    """No `user_id` field — the target user is identified by the URL path
    (`POST /users/{user_id}/roles`), the same reasoning as
    `app.modules.patient.api.schemas.RegisterPatientRequest`'s own
    docstring for why a redundant, independently-trustable identity field
    doesn't belong in the request body."""

    role_id: UUID


# --- Register / Login ----------------------------------------------------


class RegisterRequest(ORJSONModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class RegisterResponse(ORJSONModel):
    user_id: UUID
    organization_id: UUID
    email: EmailStr


class LoginRequest(ORJSONModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthenticatedPrincipalResponse(ORJSONModel):
    user_id: UUID
    organization_id: UUID
    session_id: UUID
    email: EmailStr
    permissions: list[str]


class LoginResponse(ORJSONModel):
    access_token: str
    refresh_token: str
    principal: AuthenticatedPrincipalResponse
