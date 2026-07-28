"""Unit tests for the `DoctorProfile` aggregate's invariants."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.doctor.domain.entities import DoctorProfile
from app.modules.doctor.domain.enums import Gender
from app.modules.doctor.domain.events import DoctorProfileCreated, DoctorProfileUpdated
from app.modules.doctor.domain.exceptions import (
    DoctorProfileNameRequiredError,
    InvalidConsultationFeeError,
    InvalidYearsOfExperienceError,
)
from app.shared.domain.common_value_objects import EmailAddress


def _make_profile(**overrides: object) -> DoctorProfile:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "full_name": "Dr. Jane Doe",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1985, 5, 1),
    }
    defaults.update(overrides)
    return DoctorProfile.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_profile_created_event(self) -> None:
        doctor_id = uuid4()
        profile = _make_profile(doctor_id=doctor_id)

        assert profile.doctor_id == doctor_id
        assert profile.years_of_experience == 0
        events = profile.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorProfileCreated)
        assert events[0].doctor_id == doctor_id

    def test_blank_full_name_is_rejected(self) -> None:
        with pytest.raises(DoctorProfileNameRequiredError):
            _make_profile(full_name="   ")

    def test_full_name_is_stripped(self) -> None:
        profile = _make_profile(full_name="  Dr. John Smith  ")
        assert profile.full_name == "Dr. John Smith"

    def test_negative_years_of_experience_is_rejected(self) -> None:
        with pytest.raises(InvalidYearsOfExperienceError):
            _make_profile(years_of_experience=-1)

    def test_negative_consultation_fee_is_rejected(self) -> None:
        with pytest.raises(InvalidConsultationFeeError):
            _make_profile(consultation_fee=Decimal("-10.00"))

    def test_email_is_stored_as_value_object(self) -> None:
        profile = _make_profile(email=EmailAddress("jane.doe@example.com"))
        assert str(profile.email) == "jane.doe@example.com"


class TestUpdate:
    def test_update_changes_fields_and_records_event(self) -> None:
        profile = _make_profile()
        profile.pull_events()

        profile.update(full_name="Dr. Jane A. Doe", years_of_experience=5)

        assert profile.full_name == "Dr. Jane A. Doe"
        assert profile.years_of_experience == 5
        events = profile.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorProfileUpdated)

    def test_update_rejects_blank_full_name(self) -> None:
        profile = _make_profile()
        with pytest.raises(DoctorProfileNameRequiredError):
            profile.update(full_name="   ")

    def test_update_rejects_negative_years_of_experience(self) -> None:
        profile = _make_profile()
        with pytest.raises(InvalidYearsOfExperienceError):
            profile.update(years_of_experience=-3)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        profile = _make_profile(qualification="MBBS")
        profile.update(full_name="Dr. Updated Name")
        assert profile.qualification == "MBBS"
