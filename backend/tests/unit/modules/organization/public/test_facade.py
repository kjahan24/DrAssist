"""Unit tests for `OrganizationFacade` — exercised through
`OrganizationQueryPort`/`OrganizationProvisioningPort` exactly as a future
consumer module would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract tests"
framing. `provision_organization` is exercised here (not just indirectly
through `RegisterUser`'s own fakes) because it is this facade's own new
behavior, not the peer module's.
"""

from app.modules.organization.application.services.organization_query_service import (
    OrganizationQueryService,
)
from app.modules.organization.application.use_cases.create_organization import CreateOrganization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.public.facade import OrganizationFacade
from app.modules.organization.public.interfaces import (
    OrganizationProvisioningPort,
    OrganizationQueryPort,
)
from tests.unit.modules.organization.application.fakes import (
    FakeOrganizationRepository,
    FakeOrganizationSettingsRepository,
    FakeUnitOfWork,
)


def _facade() -> tuple[OrganizationFacade, FakeOrganizationRepository]:
    organizations = FakeOrganizationRepository()
    settings = FakeOrganizationSettingsRepository()
    query_service = OrganizationQueryService(
        organization_repository=organizations, organization_settings_repository=settings
    )
    create_use_case = CreateOrganization(
        organization_repository=organizations,
        organization_settings_repository=settings,
        unit_of_work=FakeUnitOfWork(),
    )
    facade = OrganizationFacade(
        query_service=query_service, create_organization_use_case=create_use_case
    )
    return facade, organizations


class TestOrganizationFacade:
    def test_is_both_ports(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, OrganizationQueryPort)
        assert isinstance(facade, OrganizationProvisioningPort)

    async def test_provision_organization_creates_a_real_active_organization(self) -> None:
        facade, organizations = _facade()

        summary = await facade.provision_organization(name="Ada Lovelace's Organization")

        assert summary.name == "Ada Lovelace's Organization"
        assert summary.is_active is True
        assert summary.type is OrganizationType.CLINIC
        stored = await organizations.get_by_id(summary.organization_id)
        assert stored is not None

    async def test_each_call_provisions_a_distinct_organization_with_a_unique_code(self) -> None:
        facade, _ = _facade()

        first = await facade.provision_organization(name="First Org")
        second = await facade.provision_organization(name="Second Org")

        assert first.organization_id != second.organization_id
        assert first.organization_code != second.organization_code

    async def test_provisioned_organization_is_immediately_queryable(self) -> None:
        facade, _ = _facade()

        summary = await facade.provision_organization(name="Queryable Org", email="a@b.com")

        assert await facade.organization_exists(summary.organization_id) is True
        assert await facade.is_active(summary.organization_id) is True
        fetched = await facade.get_organization_summary(summary.organization_id)
        assert fetched is not None
        assert fetched.email == "a@b.com"
