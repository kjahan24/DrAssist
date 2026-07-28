"""Unit tests for the `DoctorSpecialization` aggregate's invariants."""

from uuid import uuid4

import pytest

from app.modules.doctor.domain.entities import DoctorSpecialization
from app.modules.doctor.domain.events import DoctorSpecializationAdded
from app.modules.doctor.domain.exceptions import (
    InvalidYearsOfExperienceError,
    SpecializationNameRequiredError,
)


def _make_specialization(**overrides: object) -> DoctorSpecialization:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "doctor_id": uuid4(),
        "specialization_name": "Cardiology",
    }
    defaults.update(overrides)
    return DoctorSpecialization.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_specialization_added_event(self) -> None:
        doctor_id = uuid4()
        specialization = _make_specialization(doctor_id=doctor_id)

        assert specialization.doctor_id == doctor_id
        assert specialization.is_primary is False
        events = specialization.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorSpecializationAdded)
        assert events[0].specialization_name == "Cardiology"

    def test_blank_specialization_name_is_rejected(self) -> None:
        with pytest.raises(SpecializationNameRequiredError):
            _make_specialization(specialization_name="  ")

    def test_specialization_name_is_stripped(self) -> None:
        specialization = _make_specialization(specialization_name="  Neurology  ")
        assert specialization.specialization_name == "Neurology"

    def test_negative_years_of_experience_is_rejected(self) -> None:
        with pytest.raises(InvalidYearsOfExperienceError):
            _make_specialization(years_of_experience=-1)

    def test_can_be_marked_primary(self) -> None:
        specialization = _make_specialization(is_primary=True)
        assert specialization.is_primary is True
