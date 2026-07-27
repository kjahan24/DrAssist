"""Unit tests for the `OrganizationSettings` aggregate's invariants."""

from uuid import uuid4

import pytest

from app.modules.organization.domain.entities import OrganizationSettings
from app.modules.organization.domain.events import (
    OrganizationSettingsCreated,
    OrganizationSettingsUpdated,
)
from app.modules.organization.domain.exceptions import InvalidAppointmentDurationError


class TestCreateDefault:
    def test_create_default_applies_sane_defaults(self) -> None:
        organization_id = uuid4()
        settings = OrganizationSettings.create_default(organization_id=organization_id)

        assert settings.organization_id == organization_id
        assert settings.appointment_duration_minutes == 30
        assert settings.default_timezone == "UTC"
        assert settings.default_currency == "USD"
        assert settings.working_hours == {}
        assert settings.feature_flags == {}

    def test_create_default_records_settings_created_event(self) -> None:
        settings = OrganizationSettings.create_default(organization_id=uuid4())
        events = settings.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], OrganizationSettingsCreated)
        assert events[0].settings_id == settings.id


class TestAppointmentDurationValidation:
    @pytest.mark.parametrize("minutes", [0, -1, -30])
    def test_non_positive_duration_is_rejected_at_construction(self, minutes: int) -> None:
        with pytest.raises(InvalidAppointmentDurationError):
            OrganizationSettings(organization_id=uuid4(), appointment_duration_minutes=minutes)

    def test_update_rejects_non_positive_duration(self) -> None:
        settings = OrganizationSettings.create_default(organization_id=uuid4())
        with pytest.raises(InvalidAppointmentDurationError):
            settings.update(appointment_duration_minutes=0)


class TestUpdate:
    def test_update_changes_requested_fields_and_records_event(self) -> None:
        settings = OrganizationSettings.create_default(organization_id=uuid4())
        settings.pull_events()

        settings.update(
            appointment_duration_minutes=45,
            default_timezone="America/New_York",
            feature_flags={"ai_scribe": True},
        )

        assert settings.appointment_duration_minutes == 45
        assert settings.default_timezone == "America/New_York"
        assert settings.feature_flags == {"ai_scribe": True}
        events = settings.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], OrganizationSettingsUpdated)

    def test_update_leaves_unspecified_fields_untouched(self) -> None:
        settings = OrganizationSettings.create_default(organization_id=uuid4())
        settings.update(default_currency="EUR")
        assert settings.appointment_duration_minutes == 30
        assert settings.default_timezone == "UTC"

    def test_update_working_hours_and_ai_settings(self) -> None:
        settings = OrganizationSettings.create_default(organization_id=uuid4())
        working_hours = {"monday": {"open": "09:00", "close": "17:00"}}
        ai_settings = {"enabled": True, "model": "gemini-2.5-pro"}

        settings.update(working_hours=working_hours, ai_settings=ai_settings)

        assert settings.working_hours == working_hours
        assert settings.ai_settings == ai_settings
