"""Unit tests for the `PatientContact` aggregate's invariants."""

from uuid import uuid4

from app.modules.patient.domain.entities import PatientContact
from app.modules.patient.domain.enums import ContactType
from app.modules.patient.domain.events import PatientContactAdded, PatientContactUpdated
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


def _make_contact(**overrides: object) -> PatientContact:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "contact_type": ContactType.MOBILE,
        "phone_number": PhoneNumber("+1 555 0100"),
    }
    defaults.update(overrides)
    return PatientContact.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_patient_contact_added_event(self) -> None:
        patient_id = uuid4()
        contact = _make_contact(patient_id=patient_id)

        assert contact.patient_id == patient_id
        assert contact.is_primary is False
        assert contact.is_verified is False
        events = contact.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientContactAdded)
        assert events[0].contact_type == "mobile"

    def test_can_be_created_primary_and_verified(self) -> None:
        contact = _make_contact(is_primary=True, is_verified=True)
        assert contact.is_primary is True
        assert contact.is_verified is True

    def test_email_is_optional(self) -> None:
        contact = _make_contact()
        assert contact.email is None

    def test_email_is_stored_as_value_object(self) -> None:
        contact = _make_contact(email=EmailAddress("contact@example.com"))
        assert str(contact.email) == "contact@example.com"


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        contact = _make_contact()
        contact.pull_events()

        contact.update_details(contact_type=ContactType.HOME, is_verified=True)

        assert contact.contact_type is ContactType.HOME
        assert contact.is_verified is True
        events = contact.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientContactUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        contact = _make_contact(is_primary=True)
        contact.update_details(is_verified=True)
        assert contact.is_primary is True
