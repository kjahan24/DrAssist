"""Unit tests for the `LabResultItem` aggregate."""

from uuid import uuid4

import pytest

from app.modules.lab_results.domain.entities import LabResultItem
from app.modules.lab_results.domain.enums import AbnormalFlag
from app.modules.lab_results.domain.events import LabResultItemAdded
from app.modules.lab_results.domain.exceptions import TestNameRequiredError


def _make_item(**overrides: object) -> LabResultItem:
    defaults: dict[str, object] = {
        "lab_result_id": uuid4(),
        "lab_order_item_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "result_value": "5.4",
        "abnormal_flag": AbnormalFlag.NORMAL,
    }
    defaults.update(overrides)
    return LabResultItem.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_fields_and_records_event(self) -> None:
        lab_result_id = uuid4()
        lab_order_item_id = uuid4()

        item = _make_item(
            lab_result_id=lab_result_id,
            lab_order_item_id=lab_order_item_id,
            test_code="HGB",
            test_name="Hemoglobin",
            result_value="9.8",
            result_unit="g/dL",
            reference_range="12.0-16.0 g/dL",
            abnormal_flag=AbnormalFlag.LOW,
            interpretation="Consistent with mild anemia",
        )

        assert item.lab_result_id == lab_result_id
        assert item.lab_order_item_id == lab_order_item_id
        assert item.test_code == "HGB"
        assert item.test_name == "Hemoglobin"
        assert item.result_value == "9.8"
        assert item.result_unit == "g/dL"
        assert item.reference_range == "12.0-16.0 g/dL"
        assert item.abnormal_flag is AbnormalFlag.LOW
        assert item.interpretation == "Consistent with mild anemia"
        events = item.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabResultItemAdded)
        assert events[0].lab_result_item_id == item.id
        assert events[0].lab_result_id == lab_result_id

    def test_result_unit_reference_range_and_interpretation_default_to_none(self) -> None:
        item = _make_item()
        assert item.result_unit is None
        assert item.reference_range is None
        assert item.interpretation is None

    def test_blank_test_name_is_rejected(self) -> None:
        with pytest.raises(TestNameRequiredError):
            _make_item(test_name="   ")

    def test_test_name_is_stripped(self) -> None:
        item = _make_item(test_name="  Lipid Panel  ")
        assert item.test_name == "Lipid Panel"

    def test_every_abnormal_flag_is_accepted(self) -> None:
        for flag in AbnormalFlag:
            item = _make_item(abnormal_flag=flag)
            assert item.abnormal_flag is flag
