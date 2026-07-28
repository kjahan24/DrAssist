"""Unit tests for the `PatientMedication` aggregate's invariants."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.domain.entities import PatientMedication
from app.modules.patient.domain.enums import AdherenceStatus, RouteOfAdministration
from app.modules.patient.domain.events import (
    PatientMedicationAdded,
    PatientMedicationDiscontinued,
    PatientMedicationResumed,
    PatientMedicationUpdated,
)
from app.modules.patient.domain.exceptions import (
    DosageRequiredError,
    EndDateRequiredForCompletedMedicationError,
    InvalidMedicationDateRangeError,
    MedicationNameRequiredError,
)


def _make_medication(**overrides: object) -> PatientMedication:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "medication_name": "Amoxicillin",
        "dosage": "500",
        "route": RouteOfAdministration.ORAL,
        "start_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return PatientMedication.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_patient_medication_added_event(self) -> None:
        patient_id = uuid4()
        medication = _make_medication(patient_id=patient_id)

        assert medication.patient_id == patient_id
        assert medication.is_current is True
        assert medication.adherence_status is AdherenceStatus.TAKING
        events = medication.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicationAdded)
        assert events[0].medication_name == "Amoxicillin"

    def test_blank_medication_name_is_rejected(self) -> None:
        with pytest.raises(MedicationNameRequiredError):
            _make_medication(medication_name="   ")

    def test_blank_dosage_is_rejected(self) -> None:
        with pytest.raises(DosageRequiredError):
            _make_medication(dosage="   ")

    def test_medication_name_and_dosage_are_stripped(self) -> None:
        medication = _make_medication(medication_name="  Amoxicillin  ", dosage="  500  ")
        assert medication.medication_name == "Amoxicillin"
        assert medication.dosage == "500"

    def test_end_date_before_start_date_is_rejected(self) -> None:
        with pytest.raises(InvalidMedicationDateRangeError):
            _make_medication(start_date=date(2026, 1, 10), end_date=date(2026, 1, 1))

    def test_end_date_equal_to_start_date_is_accepted(self) -> None:
        medication = _make_medication(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1))
        assert medication.end_date == date(2026, 1, 1)

    def test_is_current_true_allows_null_end_date(self) -> None:
        medication = _make_medication(is_current=True, end_date=None)
        assert medication.end_date is None

    def test_not_current_and_completed_requires_end_date(self) -> None:
        with pytest.raises(EndDateRequiredForCompletedMedicationError):
            _make_medication(
                is_current=False, adherence_status=AdherenceStatus.COMPLETED, end_date=None
            )

    def test_not_current_and_completed_with_end_date_is_accepted(self) -> None:
        medication = _make_medication(
            is_current=False,
            adherence_status=AdherenceStatus.COMPLETED,
            end_date=date(2026, 2, 1),
        )
        assert medication.end_date == date(2026, 2, 1)

    def test_not_current_and_stopped_does_not_require_end_date(self) -> None:
        medication = _make_medication(
            is_current=False, adherence_status=AdherenceStatus.STOPPED, end_date=None
        )
        assert medication.end_date is None


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        medication = _make_medication()
        medication.pull_events()

        medication.update_details(dosage="250", frequency="twice daily")

        assert medication.dosage == "250"
        assert medication.frequency == "twice daily"
        events = medication.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicationUpdated)

    def test_update_rejects_blank_medication_name(self) -> None:
        medication = _make_medication()
        with pytest.raises(MedicationNameRequiredError):
            medication.update_details(medication_name="   ")

    def test_update_rejects_blank_dosage(self) -> None:
        medication = _make_medication()
        with pytest.raises(DosageRequiredError):
            medication.update_details(dosage="   ")

    def test_update_start_date_revalidates_against_existing_end_date(self) -> None:
        medication = _make_medication(
            start_date=date(2026, 1, 1),
            is_current=False,
            adherence_status=AdherenceStatus.COMPLETED,
            end_date=date(2026, 1, 15),
        )
        with pytest.raises(InvalidMedicationDateRangeError):
            medication.update_details(start_date=date(2026, 2, 1))

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        medication = _make_medication(indication="Sinus infection")
        medication.update_details(dosage="250")
        assert medication.indication == "Sinus infection"


class TestDiscontinueAndResume:
    def test_discontinue_sets_fields_and_records_event(self) -> None:
        medication = _make_medication()
        medication.pull_events()

        medication.discontinue(end_date=date(2026, 1, 20))

        assert medication.is_current is False
        assert medication.adherence_status is AdherenceStatus.STOPPED
        assert medication.end_date == date(2026, 1, 20)
        events = medication.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicationDiscontinued)
        assert events[0].end_date == date(2026, 1, 20)

    def test_discontinue_with_completed_status(self) -> None:
        medication = _make_medication()
        medication.discontinue(
            end_date=date(2026, 1, 20), adherence_status=AdherenceStatus.COMPLETED
        )
        assert medication.adherence_status is AdherenceStatus.COMPLETED

    def test_discontinue_rejects_end_date_before_start_date(self) -> None:
        medication = _make_medication(start_date=date(2026, 1, 10))
        with pytest.raises(InvalidMedicationDateRangeError):
            medication.discontinue(end_date=date(2026, 1, 1))

    def test_resume_resets_fields_and_records_event(self) -> None:
        medication = _make_medication()
        medication.discontinue(end_date=date(2026, 1, 20))
        medication.pull_events()

        medication.resume()

        assert medication.is_current is True
        assert medication.adherence_status is AdherenceStatus.TAKING
        assert medication.end_date is None
        events = medication.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientMedicationResumed)

    def test_resuming_an_already_current_medication_is_idempotent(self) -> None:
        medication = _make_medication()
        medication.pull_events()
        medication.resume()
        assert medication.pull_events() == []
