"""Unit tests for `OrganizationQueryService` — backs the module's public
`OrganizationQueryPort` facade."""

from uuid import uuid4

import pytest

from app.modules.organization.application.services.organization_query_service import (
    OrganizationQueryService,
)
from app.modules.organization.domain.entities import Organization, OrganizationSettings
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from tests.unit.modules.organization.application.fakes import (
    FakeOrganizationRepository,
    FakeOrganizationSettingsRepository,
)


@pytest.fixture
def organization_repository() -> FakeOrganizationRepository:
    return FakeOrganizationRepository()


@pytest.fixture
def settings_repository() -> FakeOrganizationSettingsRepository:
    return FakeOrganizationSettingsRepository()


@pytest.fixture
def service(
    organization_repository: FakeOrganizationRepository,
    settings_repository: FakeOrganizationSettingsRepository,
) -> OrganizationQueryService:
    return OrganizationQueryService(
        organization_repository=organization_repository,
        organization_settings_repository=settings_repository,
    )


class TestOrganizationExists:
    async def test_true_for_a_known_organization(
        self, service: OrganizationQueryService, organization_repository: FakeOrganizationRepository
    ) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME"), name="Acme", type=OrganizationType.CLINIC
        )
        await organization_repository.add(organization)
        assert await service.organization_exists(organization.id) is True

    async def test_false_for_an_unknown_organization(
        self, service: OrganizationQueryService
    ) -> None:
        assert await service.organization_exists(uuid4()) is False


class TestIsActive:
    async def test_reflects_the_organizations_active_flag(
        self, service: OrganizationQueryService, organization_repository: FakeOrganizationRepository
    ) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME"), name="Acme", type=OrganizationType.CLINIC
        )
        await organization_repository.add(organization)
        assert await service.is_active(organization.id) is True

        organization.deactivate()
        await organization_repository.add(organization)
        assert await service.is_active(organization.id) is False

    async def test_false_for_an_unknown_organization(
        self, service: OrganizationQueryService
    ) -> None:
        assert await service.is_active(uuid4()) is False


class TestGetOrganizationSummary:
    async def test_returns_summary_for_known_organization(
        self, service: OrganizationQueryService, organization_repository: FakeOrganizationRepository
    ) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME"),
            name="Acme Clinic",
            type=OrganizationType.CLINIC,
        )
        await organization_repository.add(organization)

        summary = await service.get_organization_summary(organization.id)

        assert summary is not None
        assert summary.organization_code == "ACME"
        assert summary.name == "Acme Clinic"
        assert summary.is_active is True

    async def test_returns_none_for_unknown_organization(
        self, service: OrganizationQueryService
    ) -> None:
        assert await service.get_organization_summary(uuid4()) is None


class TestGetDefaultTimezone:
    async def test_prefers_settings_default_timezone(
        self,
        service: OrganizationQueryService,
        organization_repository: FakeOrganizationRepository,
        settings_repository: FakeOrganizationSettingsRepository,
    ) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME"),
            name="Acme",
            type=OrganizationType.CLINIC,
            timezone="UTC",
        )
        await organization_repository.add(organization)
        settings = OrganizationSettings.create_default(organization_id=organization.id)
        settings.update(default_timezone="Asia/Kolkata")
        await settings_repository.add(settings)

        assert await service.get_default_timezone(organization.id) == "Asia/Kolkata"

    async def test_falls_back_to_organization_timezone_when_no_settings_exist(
        self, service: OrganizationQueryService, organization_repository: FakeOrganizationRepository
    ) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME"),
            name="Acme",
            type=OrganizationType.CLINIC,
            timezone="Europe/London",
        )
        await organization_repository.add(organization)

        assert await service.get_default_timezone(organization.id) == "Europe/London"

    async def test_returns_none_for_unknown_organization(
        self, service: OrganizationQueryService
    ) -> None:
        assert await service.get_default_timezone(uuid4()) is None
