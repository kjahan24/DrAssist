"""Unit tests for the `Organization` aggregate's invariants — no I/O."""

from uuid import uuid4

import pytest

from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.events import (
    OrganizationActivated,
    OrganizationCreated,
    OrganizationDeactivated,
    OrganizationProfileUpdated,
)
from app.modules.organization.domain.exceptions import OrganizationNameRequiredError
from app.modules.organization.domain.value_objects import OrganizationCode


def _make_organization(**overrides: object) -> Organization:
    defaults: dict[str, object] = {
        "organization_code": OrganizationCode("ACME-CLINIC"),
        "name": "Acme Clinic",
        "type": OrganizationType.CLINIC,
    }
    defaults.update(overrides)
    return Organization(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_organization_created_event(self) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME-CLINIC"),
            name="Acme Clinic",
            type=OrganizationType.CLINIC,
        )
        events = organization.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], OrganizationCreated)
        assert events[0].organization_code == "ACME-CLINIC"
        assert events[0].name == "Acme Clinic"

    def test_create_applies_default_locale_fields(self) -> None:
        organization = Organization.create(
            organization_code=OrganizationCode("ACME-CLINIC"),
            name="Acme Clinic",
            type=OrganizationType.HOSPITAL,
        )
        assert organization.timezone == "UTC"
        assert organization.currency == "USD"
        assert organization.language == "en"
        assert organization.is_active is True


class TestNameValidation:
    def test_blank_name_is_rejected(self) -> None:
        with pytest.raises(OrganizationNameRequiredError):
            _make_organization(name="   ")

    def test_name_is_stripped(self) -> None:
        organization = _make_organization(name="  Acme Clinic  ")
        assert organization.name == "Acme Clinic"

    def test_update_profile_rejects_blank_name(self) -> None:
        organization = _make_organization()
        with pytest.raises(OrganizationNameRequiredError):
            organization.update_profile(name="   ")


class TestIdentityEquality:
    def test_two_organizations_with_same_id_are_equal(self) -> None:
        shared_id = uuid4()
        org_a = _make_organization(id=shared_id, name="Acme")
        org_b = _make_organization(id=shared_id, name="Other Name")
        assert org_a == org_b
        assert hash(org_a) == hash(org_b)


class TestUpdateProfile:
    def test_update_profile_changes_fields_and_records_event(self) -> None:
        organization = _make_organization()
        organization.pull_events()

        organization.update_profile(name="New Name", city="Springfield", currency="EUR")

        assert organization.name == "New Name"
        assert organization.city == "Springfield"
        assert organization.currency == "EUR"
        events = organization.pull_events()
        assert any(isinstance(e, OrganizationProfileUpdated) for e in events)

    def test_update_profile_leaves_unspecified_fields_untouched(self) -> None:
        organization = _make_organization(city="Old City")
        organization.update_profile(name="New Name")
        assert organization.city == "Old City"


class TestActivation:
    def test_deactivate_then_activate_round_trips(self) -> None:
        organization = _make_organization()
        organization.pull_events()

        organization.deactivate()
        assert organization.is_active is False
        deactivated_events = organization.pull_events()
        assert any(isinstance(e, OrganizationDeactivated) for e in deactivated_events)

        organization.activate()
        assert organization.is_active is True
        activated_events = organization.pull_events()
        assert any(isinstance(e, OrganizationActivated) for e in activated_events)

    def test_activating_an_already_active_organization_is_idempotent(self) -> None:
        organization = _make_organization()
        organization.pull_events()
        organization.activate()
        assert organization.pull_events() == []

    def test_deactivating_an_already_inactive_organization_is_idempotent(self) -> None:
        organization = _make_organization()
        organization.deactivate()
        organization.pull_events()
        organization.deactivate()
        assert organization.pull_events() == []
