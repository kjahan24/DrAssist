"""Unit tests for the `EmergencyContact` aggregate's invariants."""

from uuid import uuid4

import pytest

from app.modules.patient.domain.entities import EmergencyContact
from app.modules.patient.domain.events import EmergencyContactAdded, EmergencyContactUpdated
from app.modules.patient.domain.exceptions import (
    EmergencyContactNameRequiredError,
    EmergencyContactRelationshipRequiredError,
)
from app.shared.domain.common_value_objects import PhoneNumber


def _make_contact(**overrides: object) -> EmergencyContact:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "full_name": "John Doe",
        "relationship": "Spouse",
        "phone_number": PhoneNumber("+1 555 0100"),
    }
    defaults.update(overrides)
    return EmergencyContact.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_emergency_contact_added_event(self) -> None:
        patient_id = uuid4()
        contact = _make_contact(patient_id=patient_id)

        assert contact.patient_id == patient_id
        assert contact.is_primary is False
        events = contact.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], EmergencyContactAdded)

    def test_blank_full_name_is_rejected(self) -> None:
        with pytest.raises(EmergencyContactNameRequiredError):
            _make_contact(full_name="   ")

    def test_blank_relationship_is_rejected(self) -> None:
        with pytest.raises(EmergencyContactRelationshipRequiredError):
            _make_contact(relationship="   ")

    def test_full_name_and_relationship_are_stripped(self) -> None:
        contact = _make_contact(full_name="  Jane Doe  ", relationship="  Sister  ")
        assert contact.full_name == "Jane Doe"
        assert contact.relationship == "Sister"

    def test_can_be_created_primary(self) -> None:
        contact = _make_contact(is_primary=True)
        assert contact.is_primary is True


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        contact = _make_contact()
        contact.pull_events()

        contact.update_details(full_name="Jane Smith", priority=1)

        assert contact.full_name == "Jane Smith"
        assert contact.priority == 1
        events = contact.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], EmergencyContactUpdated)

    def test_update_rejects_blank_full_name(self) -> None:
        contact = _make_contact()
        with pytest.raises(EmergencyContactNameRequiredError):
            contact.update_details(full_name="   ")

    def test_update_rejects_blank_relationship(self) -> None:
        contact = _make_contact()
        with pytest.raises(EmergencyContactRelationshipRequiredError):
            contact.update_details(relationship="   ")

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        contact = _make_contact(address="123 Main St")
        contact.update_details(full_name="Updated Name")
        assert contact.address == "123 Main St"
