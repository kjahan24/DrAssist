"""Unit tests for value objects specific to the Vital Signs module."""

import pytest

from app.modules.vital_signs.domain.exceptions import InvalidBloodPressureError
from app.modules.vital_signs.domain.value_objects import BloodPressure


class TestBloodPressure:
    def test_accepts_systolic_greater_than_diastolic(self) -> None:
        bp = BloodPressure(systolic=120, diastolic=80)
        assert bp.systolic == 120
        assert bp.diastolic == 80

    def test_rejects_systolic_equal_to_diastolic(self) -> None:
        with pytest.raises(InvalidBloodPressureError):
            BloodPressure(systolic=80, diastolic=80)

    def test_rejects_systolic_less_than_diastolic(self) -> None:
        with pytest.raises(InvalidBloodPressureError):
            BloodPressure(systolic=70, diastolic=90)

    def test_string_representation(self) -> None:
        assert str(BloodPressure(systolic=120, diastolic=80)) == "120/80"

    def test_equality_is_by_value(self) -> None:
        assert BloodPressure(systolic=120, diastolic=80) == BloodPressure(
            systolic=120, diastolic=80
        )
        assert BloodPressure(systolic=120, diastolic=80) != BloodPressure(
            systolic=110, diastolic=80
        )
