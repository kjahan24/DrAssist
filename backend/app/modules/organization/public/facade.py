"""`OrganizationFacade` — the one concrete implementation of
`OrganizationQueryPort`. Constructed per-request by
`app.modules.organization.container.build_organization_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.organization.application.services.organization_query_service import (
    OrganizationQueryService,
)
from app.modules.organization.public.dto import OrganizationSummaryDTO
from app.modules.organization.public.interfaces import OrganizationQueryPort


class OrganizationFacade(OrganizationQueryPort):
    def __init__(self, *, query_service: OrganizationQueryService) -> None:
        self._query_service = query_service

    async def organization_exists(self, organization_id: UUID) -> bool:
        return await self._query_service.organization_exists(organization_id)

    async def is_active(self, organization_id: UUID) -> bool:
        return await self._query_service.is_active(organization_id)

    async def get_organization_summary(
        self, organization_id: UUID
    ) -> OrganizationSummaryDTO | None:
        return await self._query_service.get_organization_summary(organization_id)

    async def get_default_timezone(self, organization_id: UUID) -> str | None:
        return await self._query_service.get_default_timezone(organization_id)
