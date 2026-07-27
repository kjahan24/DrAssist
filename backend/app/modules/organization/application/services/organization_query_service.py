"""Read-only queries against `Organization`/`OrganizationSettings`.

Backs the module's public `OrganizationQueryPort`
(`docs/backend-architecture/03_module_architecture.md`) — this is the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.organization.application.dto import OrganizationSummaryDTO
from app.modules.organization.domain.repositories import (
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
