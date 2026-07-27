"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.organization.domain.entities import Department, Organization, OrganizationSettings
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.models import (
    DepartmentModel,
    OrganizationModel,
    OrganizationSettingsModel,
)
from app.shared.domain.common_value_objects import EmailAddress

# --- Organization ----------------------------------------------------------


def organization_to_domain(model: OrganizationModel) -> Organization:
    return Organization(
        id=model.id,
        organization_code=OrganizationCode(model.organization_code),
        name=model.name,
        type=model.type,
        legal_name=model.legal_name,
        email=EmailAddress(model.email) if model.email else None,
        phone=model.phone,
        website=model.website,
        logo_url=model.logo_url,
        tax_number=model.tax_number,
        registration_number=model.registration_number,
        address=model.address,
        city=model.city,
        state=model.state,
        country=model.country,
        postal_code=model.postal_code,
        timezone=model.timezone,
        currency=model.currency,
        language=model.language,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_organization_to_model(entity: Organization, model: OrganizationModel) -> None:
    model.id = entity.id
    model.organization_code = str(entity.organization_code)
    model.name = entity.name
    model.type = entity.type
    model.legal_name = entity.legal_name
    model.email = str(entity.email) if entity.email else None
    model.phone = entity.phone
    model.website = entity.website
    model.logo_url = entity.logo_url
    model.tax_number = entity.tax_number
    model.registration_number = entity.registration_number
    model.address = entity.address
    model.city = entity.city
    model.state = entity.state
    model.country = entity.country
    model.postal_code = entity.postal_code
    model.timezone = entity.timezone
    model.currency = entity.currency
    model.language = entity.language
    model.is_active = entity.is_active


# --- OrganizationSettings ------------------------------------------------


def organization_settings_to_domain(model: OrganizationSettingsModel) -> OrganizationSettings:
    return OrganizationSettings(
        id=model.id,
        organization_id=model.organization_id,
        working_hours=dict(model.working_hours),
        appointment_duration_minutes=model.appointment_duration_minutes,
        default_timezone=model.default_timezone,
        default_language=model.default_language,
        default_currency=model.default_currency,
        feature_flags=dict(model.feature_flags),
        ai_settings=dict(model.ai_settings),
        notification_settings=dict(model.notification_settings),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_organization_settings_to_model(
    entity: OrganizationSettings, model: OrganizationSettingsModel
) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.working_hours = dict(entity.working_hours)
    model.appointment_duration_minutes = entity.appointment_duration_minutes
    model.default_timezone = entity.default_timezone
    model.default_language = entity.default_language
    model.default_currency = entity.default_currency
    model.feature_flags = dict(entity.feature_flags)
    model.ai_settings = dict(entity.ai_settings)
    model.notification_settings = dict(entity.notification_settings)


# --- Department --------------------------------------------------------


def department_to_domain(model: DepartmentModel) -> Department:
    return Department(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_department_to_model(entity: Department, model: DepartmentModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.name = entity.name
    model.description = entity.description
    model.status = entity.status
