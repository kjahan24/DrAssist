"""Unit tests for the `LabOrderItem` aggregate."""

from uuid import uuid4

import pytest

from app.modules.lab_orders.domain.entities import LabOrderItem
from app.modules.lab_orders.domain.enums import LabOrderStatus
from app.modules.lab_orders.domain.events import LabOrderItemAdded
from app.modules.lab_orders.domain.exceptions import TestNameRequiredError


def _make_item(**overrides: object) -> LabOrderItem:
    defaults: dict[str, object] = {
        "lab_order_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "specimen_type": "Blood",
    }
    defaults.update(overrides)
    return LabOrderItem.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_fields_and_records_event(self) -> None:
        lab_order_id = uuid4()

        item = _make_item(
            lab_order_id=lab_order_id,
            test_code="URIN",
            test_name="Urinalysis",
            specimen_type="Urine",
            specimen_site="Midstream",
            instructions="Clean catch sample",
        )

        assert item.lab_order_id == lab_order_id
        assert item.test_code == "URIN"
        assert item.test_name == "Urinalysis"
        assert item.specimen_type == "Urine"
        assert item.specimen_site == "Midstream"
        assert item.instructions == "Clean catch sample"
        events = item.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabOrderItemAdded)
        assert events[0].lab_order_item_id == item.id
        assert events[0].lab_order_id == lab_order_id

    def test_default_status_is_draft(self) -> None:
        assert _make_item().status is LabOrderStatus.DRAFT

    def test_specimen_site_and_instructions_default_to_none(self) -> None:
        item = _make_item()
        assert item.specimen_site is None
        assert item.instructions is None

    def test_blank_test_name_is_rejected(self) -> None:
        with pytest.raises(TestNameRequiredError):
            _make_item(test_name="   ")

    def test_test_name_is_stripped(self) -> None:
        item = _make_item(test_name="  Lipid Panel  ")
        assert item.test_name == "Lipid Panel"
