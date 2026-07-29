"""Unit tests for the `Prescription` aggregate's own invariants: its
Draft -> Final transition and the "own status must be Draft" self-check
`ensure_editable()` shares with `update_details()`/`finalize()`.

The cross-aggregate "must have at least one item" check has no domain-
layer test here — it is enforced by
`FinalizePrescription` (see `tests/unit/modules/prescriptions/application
/test_finalize_prescription.py`), not by `Prescription.finalize()` itself.
"""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.prescriptions.domain.entities import Prescription
from app.modules.prescriptions.domain.enums import PrescriptionStatus
from app.modules.prescriptions.domain.events import (
    PrescriptionCreated,
    PrescriptionFinalized,
    PrescriptionUpdated,
)
from app.modules.prescriptions.domain.exceptions import (
    PrescriptionNotEditableError,
    PrescriptionNumberRequiredError,
)


def _make_prescription(**overrides: object) -> Prescription:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "prescription_number": "RX-0001",
        "prescription_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return Prescription.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        clinical_note_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()

        prescription = _make_prescription(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )

        assert prescription.organization_id == organization_id
        assert prescription.clinical_note_id == clinical_note_id
        assert prescription.patient_id == patient_id
        assert prescription.visit_id == visit_id
        assert prescription.doctor_id == doctor_id
        events = prescription.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PrescriptionCreated)
        assert events[0].prescription_id == prescription.id
        assert events[0].clinical_note_id == clinical_note_id

    def test_default_status_is_draft(self) -> None:
        prescription = _make_prescription()
        assert prescription.status is PrescriptionStatus.DRAFT

    def test_blank_prescription_number_is_rejected(self) -> None:
        with pytest.raises(PrescriptionNumberRequiredError):
            _make_prescription(prescription_number="   ")

    def test_prescription_number_is_stripped(self) -> None:
        prescription = _make_prescription(prescription_number="  RX-0002  ")
        assert prescription.prescription_number == "RX-0002"

    def test_notes_defaults_to_none(self) -> None:
        prescription = _make_prescription()
        assert prescription.notes is None


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_draft(self) -> None:
        prescription = _make_prescription()
        prescription.pull_events()

        prescription.update_details(prescription_date=date(2026, 2, 1), notes="Take with food")

        assert prescription.prescription_date == date(2026, 2, 1)
        assert prescription.notes == "Take with food"
        events = prescription.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PrescriptionUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        prescription = _make_prescription(notes="Original notes")
        prescription.update_details(prescription_date=date(2026, 3, 1))
        assert prescription.notes == "Original notes"

    def test_update_while_final_is_rejected(self) -> None:
        prescription = _make_prescription()
        prescription.finalize()
        with pytest.raises(PrescriptionNotEditableError):
            prescription.update_details(notes="New notes")


class TestFinalize:
    def test_finalize_sets_status_and_records_event(self) -> None:
        prescription = _make_prescription()
        prescription.pull_events()

        prescription.finalize()

        assert prescription.status is PrescriptionStatus.FINAL
        events = prescription.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PrescriptionFinalized)
        assert events[0].prescription_id == prescription.id

    def test_finalizing_an_already_final_prescription_is_rejected(self) -> None:
        prescription = _make_prescription()
        prescription.finalize()
        with pytest.raises(PrescriptionNotEditableError):
            prescription.finalize()


class TestEnsureEditable:
    def test_does_not_raise_while_draft(self) -> None:
        prescription = _make_prescription()
        prescription.ensure_editable()

    def test_raises_once_final(self) -> None:
        prescription = _make_prescription()
        prescription.finalize()
        with pytest.raises(PrescriptionNotEditableError):
            prescription.ensure_editable()
