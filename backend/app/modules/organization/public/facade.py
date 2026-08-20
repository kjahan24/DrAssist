"""`OrganizationFacade` — the one concrete implementation of
`OrganizationQueryPort` and `OrganizationProvisioningPort`. Constructed
per-request by `app.modules.organization.container.build_organization_facade`,
bound to that request's `AsyncSession`.

`_generate_organization_code` produces a `"ORG-"` + 10 hex characters
code (well within `OrganizationCode`'s 2-32 char pattern) from a random
UUID4 — collision-safe enough in practice that `provision_organization`
never needs a retry loop, unlike the `organization_code` a human enters
via `CreateOrganizationRequest`, which genuinely can collide and does
raise `DuplicateOrganizationCodeError`.
"""

from uuid import UUID, uuid4

from app.modules.organization.application.dto import CreateOrganizationInput
from app.modules.organization.application.services.organization_query_service import (
    OrganizationQueryService,
)
from app.modules.organization.application.use_cases.create_organization import CreateOrganization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.public.dto import OrganizationSummaryDTO
from app.modules.organization.public.interfaces import (
    OrganizationProvisioningPort,
    OrganizationQueryPort,
)

_SELF_SERVICE_ORGANIZATION_TYPE = OrganizationType.CLINIC


def _generate_organization_code() -> str:
    return f"ORG-{uuid4().hex[:10].upper()}"


class OrganizationFacade(OrganizationQueryPort, OrganizationProvisioningPort):
    def __init__(
        self,
        *,
        query_service: OrganizationQueryService,
        create_organization_use_case: CreateOrganization,
    ) -> None:
        self._query_service = query_service
        self._create_organization = create_organization_use_case

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

    async def provision_organization(
        self, *, name: str, email: str | None = None
    ) -> OrganizationSummaryDTO:
        output = await self._create_organization.execute(
            CreateOrganizationInput(
                organization_code=_generate_organization_code(),
                name=name,
                type=_SELF_SERVICE_ORGANIZATION_TYPE,
                email=email,
            )
        )
        summary = await self._query_service.get_organization_summary(output.organization_id)
        assert summary is not None
        return summary
