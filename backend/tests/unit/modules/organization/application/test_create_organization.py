"""Unit tests for the `CreateOrganization` use case, using in-memory fakes."""

import pytest

from app.modules.organization.application.dto import CreateOrganizationInput
from app.modules.organization.application.use_cases.create_organization import CreateOrganization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.events import OrganizationCreated, OrganizationSettingsCreated
from app.modules.organization.domain.exceptions import DuplicateOrganizationCodeError
from tests.unit.modules.organization.application.fakes import (
    FakeOrganizationRepository,
    FakeOrganizationSettingsRepository,
    FakeUnitOfWork,
)


@pytest.fixture
def organization_repository() -> FakeOrganizationRepository:
    return FakeOrganizationRepository()


@pytest.fixture
def organization_settings_repository() -> FakeOrganizationSettingsRepository:
    return FakeOrganizationSettingsRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    organization_repository: FakeOrganizationRepository,
    organization_settings_repository: FakeOrganizationSettingsRepository,
    unit_of_work: FakeUnitOfWork,
) -> CreateOrganization:
    return CreateOrganization(
        organization_repository=organization_repository,
        organization_settings_repository=organization_settings_repository,
        unit_of_work=unit_of_work,
    )


class TestCreateOrganization:
    async def test_creates_organization_and_default_settings_together(
        self,
        use_case: CreateOrganization,
        organization_repository: FakeOrganizationRepository,
        organization_settings_repository: FakeOrganizationSettingsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        output = await use_case.execute(
            CreateOrganizationInput(
                organization_code="acme-clinic",
                name="Acme Clinic",
                type=OrganizationType.CLINIC,
            )
        )

        stored_org = await organization_repository.get_by_id(output.organization_id)
        assert stored_org is not None
        assert str(stored_org.organization_code) == "ACME-CLINIC"

        stored_settings = await organization_settings_repository.get_by_organization_id(
            output.organization_id
        )
        assert stored_settings is not None
        assert stored_settings.id == output.settings_id
        assert unit_of_work.committed is True

    async def test_publishes_organization_created_and_settings_created_events(
        self, use_case: CreateOrganization, unit_of_work: FakeUnitOfWork
    ) -> None:
        await use_case.execute(
            CreateOrganizationInput(
                organization_code="acme-hospital",
                name="Acme Hospital",
                type=OrganizationType.HOSPITAL,
            )
        )

        assert any(isinstance(e, OrganizationCreated) for e in unit_of_work.published_events)
        assert any(
            isinstance(e, OrganizationSettingsCreated) for e in unit_of_work.published_events
        )

    async def test_duplicate_organization_code_is_rejected(
        self, use_case: CreateOrganization
    ) -> None:
        await use_case.execute(
            CreateOrganizationInput(
                organization_code="ACME", name="Acme One", type=OrganizationType.CLINIC
            )
        )

        with pytest.raises(DuplicateOrganizationCodeError):
            await use_case.execute(
                CreateOrganizationInput(
                    organization_code="acme", name="Acme Two", type=OrganizationType.CLINIC
                )
            )

    async def test_optional_fields_default_correctly(
        self, use_case: CreateOrganization, organization_repository: FakeOrganizationRepository
    ) -> None:
        output = await use_case.execute(
            CreateOrganizationInput(
                organization_code="MINIMAL", name="Minimal Org", type=OrganizationType.DIAGNOSTIC
            )
        )
        stored = await organization_repository.get_by_id(output.organization_id)
        assert stored is not None
        assert stored.timezone == "UTC"
        assert stored.currency == "USD"
        assert stored.language == "en"
        assert stored.email is None
