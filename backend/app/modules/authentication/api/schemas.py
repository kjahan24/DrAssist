"""Pydantic v2 request/response schemas for the Authentication module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase (login/register are explicitly out of scope; see
`container.py`). These schemas exist so the wire shape is defined ahead of
time and so `RoleResponse`/`PermissionResponse` can already back the RBAC
administration use cases' eventual endpoints.

Schemas never expose a domain entity directly, and never accept
`organization_id`/`status`/other server-controlled fields from the client
— see `docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from uuid import UUID

from pydantic import EmailStr, Field

from app.modules.authentication.domain.enums import UserStatus
from app.schemas.base import ORJSONModel


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
