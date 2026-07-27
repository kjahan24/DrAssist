"""Unit tests for the `UpdateOrganizationSettings` use case."""

from uuid import uuid4

import pytest

from app.modules.organization.application.dto import UpdateOrganizationSettingsInput
from app.modules.organization.application.use_cases.update_organization_settings import (
    UpdateOrganizationSettings,
)
from app.modules.organization.domain.entities import OrganizationSettings
from app.modules.organization.domain.events import OrganizationSettingsUpdated
from app.modules.organization.domain.exceptions import (
    InvalidAppointmentDurationError,
    OrganizationSettingsNotFoundError,
)
from tests.unit.modules.organization.application.fakes import (
    FakeOrganizationSettingsRepository,
    FakeUnitOfWork,
)


@pytest.fixture
def settings_repository() -> FakeOrganizationSettingsRepository:
    return FakeOrganizationSettingsRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    settings_repository: FakeOrganizationSettingsRepository, unit_of_work: FakeUnitOfWork
) -> UpdateOrganizationSettings:
    return UpdateOrganizationSettings(
        organization_settings_repository=settings_repository, unit_of_work=unit_of_work
    )


class TestUpdateOrganizationSettings:
    async def test_updates_existing_settings(
        self,
        use_case: UpdateOrganizationSettings,
        settings_repository: FakeOrganizationSettingsRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        settings = OrganizationSettings.create_default(organization_id=organization_id)
        await settings_repository.add(settings)

        output = await use_case.execute(
            UpdateOrganizationSettingsInput(
                organization_id=organization_id,
                appointment_duration_minutes=45,
                default_timezone="America/New_York",
            )
        )

        assert output.appointment_duration_minutes == 45
        assert output.default_timezone == "America/New_York"
        assert unit_of_work.committed is True
        assert any(
            isinstance(e, OrganizationSettingsUpdated) for e in unit_of_work.published_events
        )

    async def test_unknown_organization_raises(self, use_case: UpdateOrganizationSettings) -> None:
        with pytest.raises(OrganizationSettingsNotFoundError):
            await use_case.execute(
                UpdateOrganizationSettingsInput(
                    organization_id=uuid4(), appointment_duration_minutes=45
                )
            )

    async def test_invalid_duration_is_rejected(
        self,
        use_case: UpdateOrganizationSettings,
        settings_repository: FakeOrganizationSettingsRepository,
    ) -> None:
        organization_id = uuid4()
        settings = OrganizationSettings.create_default(organization_id=organization_id)
        await settings_repository.add(settings)

        with pytest.raises(InvalidAppointmentDurationError):
            await use_case.execute(
                UpdateOrganizationSettingsInput(
                    organization_id=organization_id, appointment_duration_minutes=-5
                )
            )
