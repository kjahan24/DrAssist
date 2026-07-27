"""Pydantic v2 request/response schemas for the Organization module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `is_active`, ...) from the client —
see `docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from typing import Any
from uuid import UUID

from pydantic import EmailStr, Field

from app.modules.organization.domain.enums import DepartmentStatus, OrganizationType
from app.schemas.base import ORJSONModel


class OrganizationResponse(ORJSONModel):
    id: UUID
    organization_code: str
    name: str
    legal_name: str | None = None
    type: OrganizationType
    email: EmailStr | None = None
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    tax_number: str | None = None
    registration_number: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    timezone: str
    currency: str
    language: str
    is_active: bool


class OrganizationSettingsResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    working_hours: dict[str, Any]
    appointment_duration_minutes: int
    default_timezone: str
    default_language: str
    default_currency: str
    feature_flags: dict[str, bool]
    ai_settings: dict[str, Any]
    notification_settings: dict[str, Any]


class DepartmentResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    status: DepartmentStatus


class CreateOrganizationRequest(ORJSONModel):
    organization_code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    type: OrganizationType
    legal_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    website: str | None = Field(default=None, max_length=200)
    tax_number: str | None = Field(default=None, max_length=64)
    registration_number: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    timezone: str = "UTC"
    currency: str = "USD"
    language: str = "en"


class UpdateOrganizationSettingsRequest(ORJSONModel):
    working_hours: dict[str, Any] | None = None
    appointment_duration_minutes: int | None = Field(default=None, gt=0)
    default_timezone: str | None = None
    default_language: str | None = None
    default_currency: str | None = None
    feature_flags: dict[str, bool] | None = None
    ai_settings: dict[str, Any] | None = None
    notification_settings: dict[str, Any] | None = None


class CreateDepartmentRequest(ORJSONModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
