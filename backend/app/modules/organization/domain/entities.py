"""Organization module aggregate roots: Organization, OrganizationSettings,
Department.

Each aggregate reference to another aggregate is by ID only (never an
object reference) — see the aggregate-reference rule in
`docs/backend-architecture/03_module_architecture.md`. `OrganizationSettings`
and `Department` are modeled as their own aggregates (not child entities of
`Organization`) for the same reason `OrganizationLocation` was kept
independent of `Organization` in the architecture design: they're edited
independently and don't need to be loaded/locked together with the parent
for any invariant this module enforces. All mutation goes through named
methods that enforce the aggregate's invariants and record domain events;
nothing here performs I/O.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.modules.organization.domain.enums import DepartmentStatus, OrganizationType
from app.modules.organization.domain.events import (
    DepartmentCreated,
    DepartmentStatusChanged,
    DepartmentUpdated,
    OrganizationActivated,
    OrganizationCreated,
    OrganizationDeactivated,
    OrganizationProfileUpdated,
    OrganizationSettingsCreated,
    OrganizationSettingsUpdated,
)
from app.modules.organization.domain.exceptions import (
    DepartmentNameRequiredError,
    InvalidAppointmentDurationError,
    OrganizationNameRequiredError,
)
from app.modules.organization.domain.value_objects import OrganizationCode
from app.shared.domain.common_value_objects import EmailAddress
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Organization(AggregateRoot):
    organization_code: OrganizationCode
    name: str
    type: OrganizationType
    legal_name: str | None = None
    email: EmailAddress | None = None
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
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise OrganizationNameRequiredError()
        self.name = self.name.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_code: OrganizationCode,
        name: str,
        type: OrganizationType,
        legal_name: str | None = None,
        email: EmailAddress | None = None,
        phone: str | None = None,
        website: str | None = None,
        logo_url: str | None = None,
        tax_number: str | None = None,
        registration_number: str | None = None,
        address: str | None = None,
        city: str | None = None,
        state: str | None = None,
        country: str | None = None,
        postal_code: str | None = None,
        timezone: str = "UTC",
        currency: str = "USD",
        language: str = "en",
    ) -> "Organization":
        organization = cls(
            organization_code=organization_code,
            name=name,
            type=type,
            legal_name=legal_name,
            email=email,
            phone=phone,
            website=website,
            logo_url=logo_url,
            tax_number=tax_number,
            registration_number=registration_number,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            timezone=timezone,
            currency=currency,
            language=language,
        )
        organization.record_event(
            OrganizationCreated(
                organization_id=organization.id,
                organization_code=str(organization_code),
                name=organization.name,
            )
        )
        return organization

    def update_profile(
        self,
        *,
        name: str | None = None,
        legal_name: str | None = None,
        type: OrganizationType | None = None,
        email: EmailAddress | None = None,
        phone: str | None = None,
        website: str | None = None,
        logo_url: str | None = None,
        tax_number: str | None = None,
        registration_number: str | None = None,
        address: str | None = None,
        city: str | None = None,
        state: str | None = None,
        country: str | None = None,
        postal_code: str | None = None,
        timezone: str | None = None,
        currency: str | None = None,
        language: str | None = None,
    ) -> None:
        if name is not None:
            if not name.strip():
                raise OrganizationNameRequiredError()
            self.name = name.strip()
        if legal_name is not None:
            self.legal_name = legal_name
        if type is not None:
            self.type = type
        if email is not None:
            self.email = email
        if phone is not None:
            self.phone = phone
        if website is not None:
            self.website = website
        if logo_url is not None:
            self.logo_url = logo_url
        if tax_number is not None:
            self.tax_number = tax_number
        if registration_number is not None:
            self.registration_number = registration_number
        if address is not None:
            self.address = address
        if city is not None:
            self.city = city
        if state is not None:
            self.state = state
        if country is not None:
            self.country = country
        if postal_code is not None:
            self.postal_code = postal_code
        if timezone is not None:
            self.timezone = timezone
        if currency is not None:
            self.currency = currency
        if language is not None:
            self.language = language

        self.touch()
        self.record_event(OrganizationProfileUpdated(organization_id=self.id))

    def activate(self) -> None:
        if self.is_active:
            return
        self.is_active = True
        self.touch()
        self.record_event(OrganizationActivated(organization_id=self.id))

    def deactivate(self) -> None:
        if not self.is_active:
            return
        self.is_active = False
        self.touch()
        self.record_event(OrganizationDeactivated(organization_id=self.id))


@dataclass(kw_only=True, eq=False)
class OrganizationSettings(AggregateRoot):
    organization_id: UUID
    working_hours: dict[str, Any] = field(default_factory=dict)
    appointment_duration_minutes: int = 30
    default_timezone: str = "UTC"
    default_language: str = "en"
    default_currency: str = "USD"
    feature_flags: dict[str, bool] = field(default_factory=dict)
    ai_settings: dict[str, Any] = field(default_factory=dict)
    notification_settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.appointment_duration_minutes <= 0:
            raise InvalidAppointmentDurationError(self.appointment_duration_minutes)

    @classmethod
    def create_default(cls, *, organization_id: UUID) -> "OrganizationSettings":
        """The only way an `OrganizationSettings` row comes into existence —
        called once, from `CreateOrganization`, immediately after the owning
        `Organization` is created. There is deliberately no standalone
        "create settings" use case, which is what makes the one-to-one
        invariant impossible to violate by construction rather than
        something that has to be checked for. See
        `application/use_cases/create_organization.py`.
        """
        settings = cls(organization_id=organization_id)
        settings.record_event(
            OrganizationSettingsCreated(organization_id=organization_id, settings_id=settings.id)
        )
        return settings

    def update(
        self,
        *,
        working_hours: dict[str, Any] | None = None,
        appointment_duration_minutes: int | None = None,
        default_timezone: str | None = None,
        default_language: str | None = None,
        default_currency: str | None = None,
        feature_flags: dict[str, bool] | None = None,
        ai_settings: dict[str, Any] | None = None,
        notification_settings: dict[str, Any] | None = None,
    ) -> None:
        if working_hours is not None:
            self.working_hours = working_hours
        if appointment_duration_minutes is not None:
            if appointment_duration_minutes <= 0:
                raise InvalidAppointmentDurationError(appointment_duration_minutes)
            self.appointment_duration_minutes = appointment_duration_minutes
        if default_timezone is not None:
            self.default_timezone = default_timezone
        if default_language is not None:
            self.default_language = default_language
        if default_currency is not None:
            self.default_currency = default_currency
        if feature_flags is not None:
            self.feature_flags = feature_flags
        if ai_settings is not None:
            self.ai_settings = ai_settings
        if notification_settings is not None:
            self.notification_settings = notification_settings

        self.touch()
        self.record_event(
            OrganizationSettingsUpdated(organization_id=self.organization_id, settings_id=self.id)
        )


@dataclass(kw_only=True, eq=False)
class Department(AggregateRoot):
    organization_id: UUID
    name: str
    description: str | None = None
    status: DepartmentStatus = DepartmentStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise DepartmentNameRequiredError()
        self.name = self.name.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        name: str,
        description: str | None = None,
    ) -> "Department":
        department = cls(organization_id=organization_id, name=name, description=description)
        department.record_event(
            DepartmentCreated(
                department_id=department.id,
                organization_id=organization_id,
                name=department.name,
            )
        )
        return department

    def update_details(self, *, name: str | None = None, description: str | None = None) -> None:
        if name is not None:
            if not name.strip():
                raise DepartmentNameRequiredError()
            self.name = name.strip()
        if description is not None:
            self.description = description
        self.touch()
        self.record_event(
            DepartmentUpdated(department_id=self.id, organization_id=self.organization_id)
        )

    def activate(self) -> None:
        self._set_status(DepartmentStatus.ACTIVE)

    def deactivate(self) -> None:
        self._set_status(DepartmentStatus.INACTIVE)

    def _set_status(self, status: DepartmentStatus) -> None:
        if self.status is status:
            return
        self.status = status
        self.touch()
        self.record_event(
            DepartmentStatusChanged(
                department_id=self.id, organization_id=self.organization_id, status=status.value
            )
        )
