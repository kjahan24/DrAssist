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


class PermissionResponse(ORJSONModel):
    id: UUID
    code: str
    module: str
    description: str


class CreateRoleRequest(ORJSONModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class AssignPermissionToRoleRequest(ORJSONModel):
    permission_code: str = Field(min_length=1, max_length=100)


class AssignRoleToUserRequest(ORJSONModel):
    user_id: UUID
    role_id: UUID
