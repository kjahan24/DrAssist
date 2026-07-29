"""Unit tests for the `PrescriptionItem` aggregate."""

from uuid import uuid4

import pytest

from app.modules.prescriptions.domain.entities import PrescriptionItem
from app.modules.prescriptions.domain.enums import AdministrationRoute
from app.modules.prescriptions.domain.events import PrescriptionItemAdded
from app.modules.prescriptions.domain.exceptions import MedicationNameRequiredError


def _make_item(**overrides: object) -> PrescriptionItem:
    defaults: dict[str, object] = {
        "prescription_id": uuid4(),
        "medication_name": "Amoxicillin",
        "strength": "500mg",
        "dosage": "1",
        "dosage_unit": "tablet",
        "frequency": "three times daily",
        "route": AdministrationRoute.ORAL,
        "duration": "7",
        "duration_unit": "days",
        "quantity": "21",
    }
    defaults.update(overrides)
    return PrescriptionItem.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_fields_and_records_event(self) -> None:
        prescription_id = uuid4()

        item = _make_item(
            prescription_id=prescription_id,
            medication_name="Ibuprofen",
            generic_name="Ibuprofen",
            strength="200mg",
            dosage="2",
            dosage_unit="tablet",
            frequency="twice daily",
            route=AdministrationRoute.ORAL,
            duration="5",
            duration_unit="days",
            quantity="20",
            instructions="Take with food",
        )

        assert item.prescription_id == prescription_id
        assert item.medication_name == "Ibuprofen"
        assert item.generic_name == "Ibuprofen"
        assert item.strength == "200mg"
        assert item.dosage == "2"
        assert item.dosage_unit == "tablet"
        assert item.frequency == "twice daily"
        assert item.route is AdministrationRoute.ORAL
        assert item.duration == "5"
        assert item.duration_unit == "days"
        assert item.quantity == "20"
        assert item.instructions == "Take with food"
        events = item.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PrescriptionItemAdded)
        assert events[0].prescription_item_id == item.id
        assert events[0].prescription_id == prescription_id

    def test_generic_name_and_instructions_default_to_none(self) -> None:
        item = _make_item()
        assert item.generic_name is None
        assert item.instructions is None

    def test_blank_medication_name_is_rejected(self) -> None:
        with pytest.raises(MedicationNameRequiredError):
            _make_item(medication_name="   ")

    def test_medication_name_is_stripped(self) -> None:
        item = _make_item(medication_name="  Paracetamol  ")
        assert item.medication_name == "Paracetamol"

    def test_every_administration_route_is_accepted(self) -> None:
        for route in AdministrationRoute:
            item = _make_item(route=route)
            assert item.route is route
