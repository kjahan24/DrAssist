"""Read-only queries against `Organization`/`OrganizationSettings`.

Backs the module's public `OrganizationQueryPort`
(`docs/backend-architecture/03_module_architecture.md`) — this is the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.organization.application.dto import (
    DepartmentSummaryDTO,
    OrganizationSettingsSummaryDTO,
    OrganizationSummaryDTO,
)
from app.modules.organization.domain.entities import Department
from app.modules.organization.domain.enums import DepartmentStatus
from app.modules.organization.domain.repositories import (
    DepartmentRepository,
    OrganizationRepository,
    OrganizationSettingsRepository,
)


class OrganizationQueryService:
    def __init__(
        self,
        *,
        organization_repository: OrganizationRepository,
        organization_settings_repository: OrganizationSettingsRepository,
    ) -> None:
        self._organizations = organization_repository
        self._settings = organization_settings_repository

    async def organization_exists(self, organization_id: UUID) -> bool:
        return await self._organizations.get_by_id(organization_id) is not None

    async def is_active(self, organization_id: UUID) -> bool:
        organization = await self._organizations.get_by_id(organization_id)
        return organization is not None and organization.is_active

    async def get_organization_summary(
        self, organization_id: UUID
    ) -> OrganizationSummaryDTO | None:
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            return None
        return OrganizationSummaryDTO(
            organization_id=organization.id,
            organization_code=str(organization.organization_code),
            name=organization.name,
            type=organization.type,
            is_active=organization.is_active,
            timezone=organization.timezone,
            currency=organization.currency,
            language=organization.language,
            legal_name=organization.legal_name,
            email=str(organization.email) if organization.email is not None else None,
            phone=organization.phone,
            website=organization.website,
            logo_url=organization.logo_url,
            tax_number=organization.tax_number,
            registration_number=organization.registration_number,
            address=organization.address,
            city=organization.city,
            state=organization.state,
            country=organization.country,
            postal_code=organization.postal_code,
        )

    async def get_organization_settings_summary(
        self, organization_id: UUID
    ) -> OrganizationSettingsSummaryDTO | None:
        settings = await self._settings.get_by_organization_id(organization_id)
        if settings is None:
            return None
        return OrganizationSettingsSummaryDTO(
            organization_id=settings.organization_id,
            settings_id=settings.id,
            appointment_duration_minutes=settings.appointment_duration_minutes,
            default_timezone=settings.default_timezone,
            default_language=settings.default_language,
            default_currency=settings.default_currency,
            feature_flags=settings.feature_flags,
            working_hours=settings.working_hours,
            ai_settings=settings.ai_settings,
            notification_settings=settings.notification_settings,
        )

    async def get_default_timezone(self, organization_id: UUID) -> str | None:
        """Prefers the organization's configured `default_timezone` setting;
        falls back to the organization's own `timezone` field if no settings
        row exists (should not happen in practice — every organization gets
        default settings at creation — but this stays correct even if that
        invariant is ever violated by direct data manipulation)."""
        settings = await self._settings.get_by_organization_id(organization_id)
        if settings is not None:
            return settings.default_timezone

        organization = await self._organizations.get_by_id(organization_id)
        return organization.timezone if organization is not None else None


class DepartmentQueryService:
    """Read-only queries for `Department` — added by the REST APIs task.

    A separate, single-repository class rather than a third constructor
    parameter on `OrganizationQueryService`: that service backs the
    public `OrganizationQueryPort` consumed by other modules (Doctor,
    Patient, ...) via `build_organization_facade`, so adding a required
    `department_repository` parameter there would break every existing
    caller. See
    `app.modules.patient.application.services.patient_sub_resource_query_service`'s
    own docstring for the full reasoning (identical situation).
    """

    def __init__(self, *, department_repository: DepartmentRepository) -> None:
        self._departments = department_repository

    async def get_department_summary(self, department_id: UUID) -> DepartmentSummaryDTO | None:
        department = await self._departments.get_by_id(department_id)
        return _department_to_summary(department) if department is not None else None

    async def list_departments_for_organization(
        self, organization_id: UUID
    ) -> list[DepartmentSummaryDTO]:
        departments = await self._departments.list_by_organization(
            organization_id, offset=0, limit=1000
        )
        return [_department_to_summary(department) for department in departments]

    async def search_departments(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[DepartmentStatus] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[DepartmentSummaryDTO], int]:
        """Search & Filtering module — see `DepartmentRepository.search`'s
        docstring for filter/sort/pagination semantics."""
        departments, total = await self._departments.search(
            organization_id=organization_id,
            query=query,
            statuses=statuses,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return [_department_to_summary(department) for department in departments], total


def _department_to_summary(department: Department) -> DepartmentSummaryDTO:
    return DepartmentSummaryDTO(
        department_id=department.id,
        organization_id=department.organization_id,
        name=department.name,
        description=department.description,
        status=department.status,
    )
