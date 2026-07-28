"""Unit tests for the `Patient` aggregate's invariants."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import BloodGroup, Gender, MaritalStatus, PatientStatus
from app.modules.patient.domain.events import (
    PatientDetailsUpdated,
    PatientRegistered,
    PatientStatusChanged,
)
from app.modules.patient.domain.exceptions import (
    FirstNameRequiredError,
    FutureDateOfBirthError,
    LastNameRequiredError,
    PatientNumberRequiredError,
)
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


def _make_patient(**overrides: object) -> Patient:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_number": "PAT-001",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1990, 1, 1),
    }
    defaults.update(overrides)
    return Patient.register(**defaults)  # type: ignore[arg-type]


class TestRegister:
    def test_register_records_patient_registered_event(self) -> None:
        organization_id = uuid4()
        patient = _make_patient(organization_id=organization_id, patient_number="PAT-42")

        assert patient.organization_id == organization_id
        assert patient.status is PatientStatus.ACTIVE
        events = patient.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientRegistered)
        assert events[0].patient_number == "PAT-42"

    def test_blank_patient_number_is_rejected(self) -> None:
        with pytest.raises(PatientNumberRequiredError):
            _make_patient(patient_number="   ")

    def test_patient_number_is_stripped(self) -> None:
        patient = _make_patient(patient_number="  PAT-999  ")
        assert patient.patient_number == "PAT-999"

    def test_blank_first_name_is_rejected(self) -> None:
        with pytest.raises(FirstNameRequiredError):
            _make_patient(first_name="   ")

    def test_blank_last_name_is_rejected(self) -> None:
        with pytest.raises(LastNameRequiredError):
            _make_patient(last_name="   ")

    def test_names_are_stripped(self) -> None:
        patient = _make_patient(first_name="  Jane  ", last_name="  Doe  ")
        assert patient.first_name == "Jane"
        assert patient.last_name == "Doe"

    def test_future_date_of_birth_is_rejected(self) -> None:
        with pytest.raises(FutureDateOfBirthError):
            _make_patient(date_of_birth=date.today() + timedelta(days=1))

    def test_todays_date_of_birth_is_accepted(self) -> None:
        patient = _make_patient(date_of_birth=date.today())
        assert patient.date_of_birth == date.today()

    def test_optional_fields_default_to_none(self) -> None:
        patient = _make_patient()
        assert patient.middle_name is None
        assert patient.blood_group is None
        assert patient.marital_status is None
        assert patient.phone is None
        assert patient.email is None

    def test_email_and_phone_are_stored_as_value_objects(self) -> None:
        patient = _make_patient(
            email=EmailAddress("jane.doe@example.com"), phone=PhoneNumber("+1 555 0100")
        )
        assert str(patient.email) == "jane.doe@example.com"
        assert str(patient.phone) == "+1 555 0100"


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        patient = _make_patient()
        patient.pull_events()

        patient.update_details(
            first_name="Janet", blood_group=BloodGroup.O_POSITIVE, city="Springfield"
        )

        assert patient.first_name == "Janet"
        assert patient.blood_group is BloodGroup.O_POSITIVE
        assert patient.city == "Springfield"
        events = patient.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientDetailsUpdated)

    def test_update_rejects_blank_first_name(self) -> None:
        patient = _make_patient()
        with pytest.raises(FirstNameRequiredError):
            patient.update_details(first_name="   ")

    def test_update_rejects_blank_last_name(self) -> None:
        patient = _make_patient()
        with pytest.raises(LastNameRequiredError):
            patient.update_details(last_name="   ")

    def test_update_rejects_future_date_of_birth(self) -> None:
        patient = _make_patient()
        with pytest.raises(FutureDateOfBirthError):
            patient.update_details(date_of_birth=date.today() + timedelta(days=1))

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        patient = _make_patient(marital_status=MaritalStatus.SINGLE)
        patient.update_details(city="Springfield")
        assert patient.marital_status is MaritalStatus.SINGLE


class TestStatusTransitions:
    def test_deactivate_then_activate_round_trips(self) -> None:
        patient = _make_patient()
        patient.pull_events()

        patient.deactivate()
        assert patient.status is PatientStatus.INACTIVE
        events = patient.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientStatusChanged)
        assert events[0].status == "inactive"

        patient.activate()
        assert patient.status is PatientStatus.ACTIVE

    def test_mark_deceased_records_event(self) -> None:
        patient = _make_patient()
        patient.pull_events()

        patient.mark_deceased()
        assert patient.status is PatientStatus.DECEASED
        events = patient.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientStatusChanged)
        assert events[0].status == "deceased"

    def test_activating_an_already_active_patient_is_idempotent(self) -> None:
        patient = _make_patient()
        patient.pull_events()
        patient.activate()
        assert patient.pull_events() == []
