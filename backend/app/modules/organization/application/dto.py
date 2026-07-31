"""Data Transfer Objects for the Organization module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `OrganizationSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.modules.organization.domain.enums import DepartmentStatus, OrganizationType

# --- CreateOrganization --------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateOrganizationInput:
    organization_code: str
    name: str
    type: OrganizationType
    legal_name: str | None = None
    email: str | None = None
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
    timezone: str = "UTC"
    currency: str = "USD"
    language: str = "en"
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateOrganizationOutput:
    organization_id: UUID
    organization_code: str
    name: str
    type: OrganizationType
    settings_id: UUID


# --- UpdateOrganizationSettings ------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateOrganizationSettingsInput:
    organization_id: UUID
    working_hours: dict[str, Any] | None = None
    appointment_duration_minutes: int | None = None
    default_timezone: str | None = None
    default_language: str | None = None
    default_currency: str | None = None
    feature_flags: dict[str, bool] | None = None
    ai_settings: dict[str, Any] | None = None
    notification_settings: dict[str, Any] | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateOrganizationSettingsOutput:
    organization_id: UUID
    settings_id: UUID
    appointment_duration_minutes: int
    default_timezone: str


# --- CreateDepartment -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateDepartmentInput:
    organization_id: UUID
    name: str
    description: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateDepartmentOutput:
    department_id: UUID
    organization_id: UUID
    name: str
    status: DepartmentStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) ----


@dataclass(frozen=True, slots=True)
class OrganizationSummaryDTO:
    organization_id: UUID
    organization_code: str
    name: str
    type: OrganizationType
    is_active: bool
    timezone: str
    currency: str
    language: str
    legal_name: str | None = None
    email: str | None = None
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

    @property
    def id(self) -> UUID:
        """Alias for `organization_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.organization_id


@dataclass(frozen=True, slots=True)
class OrganizationSettingsSummaryDTO:
    organization_id: UUID
    settings_id: UUID
    appointment_duration_minutes: int
    default_timezone: str
    default_language: str
    default_currency: str
    feature_flags: dict[str, bool] = field(default_factory=dict)
    working_hours: dict[str, Any] = field(default_factory=dict)
    ai_settings: dict[str, Any] = field(default_factory=dict)
    notification_settings: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> UUID:
        """Alias for `settings_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.settings_id


# --- Sub-resource read models (added by the REST APIs task) ----------------
# See `app.modules.patient.application.dto`'s own "Sub-resource read
# models" section for the full reasoning — identical situation here:
# `DepartmentSummaryDTO` and the query service that builds it
# (`DepartmentQueryService`, appended to
# `application/services/organization_query_service.py`) did not exist
# before this task.


@dataclass(frozen=True, slots=True)
class DepartmentSummaryDTO:
    department_id: UUID
    organization_id: UUID
    name: str
    description: str | None
    status: DepartmentStatus

    @property
    def id(self) -> UUID:
        """Alias for `department_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.department_id
