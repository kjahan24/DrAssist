"""Unit tests for the `PatientAllergy` aggregate's invariants."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.domain.entities import PatientAllergy
from app.modules.patient.domain.enums import AllergySeverity, AllergyStatus, AllergyType
from app.modules.patient.domain.events import (
    PatientAllergyRecorded,
    PatientAllergyStatusChanged,
    PatientAllergyUpdated,
    PatientAllergyVerified,
)
from app.modules.patient.domain.exceptions import (
    AllergenNameRequiredError,
    VerifiedDateRequiresVerifiedByError,
)


def _make_allergy(**overrides: object) -> PatientAllergy:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "allergy_type": AllergyType.DRUG,
        "allergen_name": "Penicillin",
        "severity": AllergySeverity.SEVERE,
    }
    defaults.update(overrides)
    return PatientAllergy.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_patient_allergy_recorded_event(self) -> None:
        patient_id = uuid4()
        allergy = _make_allergy(patient_id=patient_id)

        assert allergy.patient_id == patient_id
        assert allergy.status is AllergyStatus.ACTIVE
        events = allergy.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientAllergyRecorded)
        assert events[0].allergen_name == "Penicillin"
        assert events[0].severity == "severe"

    def test_blank_allergen_name_is_rejected(self) -> None:
        with pytest.raises(AllergenNameRequiredError):
            _make_allergy(allergen_name="   ")

    def test_allergen_name_is_stripped(self) -> None:
        allergy = _make_allergy(allergen_name="  Peanuts  ")
        assert allergy.allergen_name == "Peanuts"

    def test_verified_date_without_verified_by_is_rejected(self) -> None:
        with pytest.raises(VerifiedDateRequiresVerifiedByError):
            _make_allergy(verified_date=date(2026, 1, 1))

    def test_verified_by_without_verified_date_is_accepted(self) -> None:
        doctor_id = uuid4()
        allergy = _make_allergy(verified_by=doctor_id)
        assert allergy.verified_by == doctor_id
        assert allergy.verified_date is None

    def test_verified_by_and_verified_date_together_are_accepted(self) -> None:
        doctor_id = uuid4()
        allergy = _make_allergy(verified_by=doctor_id, verified_date=date(2026, 1, 1))
        assert allergy.verified_by == doctor_id
        assert allergy.verified_date == date(2026, 1, 1)

    def test_optional_fields_default_to_none(self) -> None:
        allergy = _make_allergy()
        assert allergy.reaction is None
        assert allergy.onset_date is None
        assert allergy.notes is None
        assert allergy.verified_by is None
        assert allergy.verified_date is None


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        allergy = _make_allergy()
        allergy.pull_events()

        allergy.update_details(reaction="Hives", severity=AllergySeverity.MODERATE)

        assert allergy.reaction == "Hives"
        assert allergy.severity is AllergySeverity.MODERATE
        events = allergy.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientAllergyUpdated)

    def test_update_rejects_blank_allergen_name(self) -> None:
        allergy = _make_allergy()
        with pytest.raises(AllergenNameRequiredError):
            allergy.update_details(allergen_name="   ")

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        allergy = _make_allergy(notes="Confirmed by patient history")
        allergy.update_details(reaction="Rash")
        assert allergy.notes == "Confirmed by patient history"


class TestVerify:
    def test_verify_sets_both_fields_and_records_event(self) -> None:
        allergy = _make_allergy()
        allergy.pull_events()
        doctor_id = uuid4()

        allergy.verify(verified_by=doctor_id, verified_date=date(2026, 1, 1))

        assert allergy.verified_by == doctor_id
        assert allergy.verified_date == date(2026, 1, 1)
        events = allergy.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientAllergyVerified)
        assert events[0].verified_by == doctor_id


class TestStatusTransitions:
    def test_resolve_then_reactivate_round_trips(self) -> None:
        allergy = _make_allergy()
        allergy.pull_events()

        allergy.resolve()
        assert allergy.status is AllergyStatus.RESOLVED
        events = allergy.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientAllergyStatusChanged)
        assert events[0].status == "resolved"

        allergy.reactivate()
        assert allergy.status is AllergyStatus.ACTIVE

    def test_resolving_an_already_resolved_allergy_is_idempotent(self) -> None:
        allergy = _make_allergy()
        allergy.resolve()
        allergy.pull_events()
        allergy.resolve()
        assert allergy.pull_events() == []
