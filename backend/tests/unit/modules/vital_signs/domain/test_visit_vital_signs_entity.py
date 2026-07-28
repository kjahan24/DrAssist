"""Unit tests for the `VisitVitalSigns` aggregate's invariants and its
`calculate_bmi` helper."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.vital_signs.domain.entities import VisitVitalSigns, calculate_bmi
from app.modules.vital_signs.domain.events import VisitVitalSignsRecorded, VisitVitalSignsUpdated
from app.modules.vital_signs.domain.exceptions import (
    InvalidPainScoreError,
    InvalidPulseError,
    InvalidRespiratoryRateError,
    InvalidSpo2Error,
    InvalidTemperatureError,
)
from app.modules.vital_signs.domain.value_objects import BloodPressure

_DEFAULT_BP = BloodPressure(systolic=120, diastolic=80)


def _make_vital_signs(**overrides: object) -> VisitVitalSigns:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "temperature_c": Decimal("37.0"),
        "pulse_bpm": 72,
        "respiratory_rate": 16,
        "blood_pressure": _DEFAULT_BP,
        "spo2": 98,
        "recorded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitVitalSigns.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_visit_vital_signs_recorded_event(self) -> None:
        organization_id = uuid4()
        visit_id = uuid4()
        vital_signs = _make_vital_signs(organization_id=organization_id, visit_id=visit_id)

        assert vital_signs.organization_id == organization_id
        assert vital_signs.visit_id == visit_id
        events = vital_signs.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitVitalSignsRecorded)

    def test_bmi_is_none_without_height_and_weight(self) -> None:
        vital_signs = _make_vital_signs()
        assert vital_signs.bmi is None

    def test_bmi_is_calculated_when_height_and_weight_are_present(self) -> None:
        vital_signs = _make_vital_signs(height_cm=Decimal("170"), weight_kg=Decimal("70"))
        assert vital_signs.bmi == Decimal("24.2")

    def test_create_rejects_a_bmi_keyword_argument(self) -> None:
        """`bmi` isn't a `create()` parameter at all, so a caller cannot
        smuggle in an inconsistent value — it is always derived from
        `height_cm`/`weight_kg`."""
        with pytest.raises(TypeError):
            _make_vital_signs(bmi=Decimal("99.9"))

    @pytest.mark.parametrize("value", [Decimal("24.9"), Decimal("45.1")])
    def test_temperature_outside_reasonable_range_is_rejected(self, value: Decimal) -> None:
        with pytest.raises(InvalidTemperatureError):
            _make_vital_signs(temperature_c=value)

    @pytest.mark.parametrize("value", [Decimal("25.0"), Decimal("45.0")])
    def test_temperature_at_range_boundary_is_accepted(self, value: Decimal) -> None:
        vital_signs = _make_vital_signs(temperature_c=value)
        assert vital_signs.temperature_c == value

    @pytest.mark.parametrize("value", [0, -1])
    def test_non_positive_pulse_is_rejected(self, value: int) -> None:
        with pytest.raises(InvalidPulseError):
            _make_vital_signs(pulse_bpm=value)

    @pytest.mark.parametrize("value", [0, -1])
    def test_non_positive_respiratory_rate_is_rejected(self, value: int) -> None:
        with pytest.raises(InvalidRespiratoryRateError):
            _make_vital_signs(respiratory_rate=value)

    @pytest.mark.parametrize("value", [-1, 101])
    def test_spo2_outside_range_is_rejected(self, value: int) -> None:
        with pytest.raises(InvalidSpo2Error):
            _make_vital_signs(spo2=value)

    @pytest.mark.parametrize("value", [0, 100])
    def test_spo2_at_range_boundary_is_accepted(self, value: int) -> None:
        vital_signs = _make_vital_signs(spo2=value)
        assert vital_signs.spo2 == value

    def test_pain_score_none_is_accepted(self) -> None:
        vital_signs = _make_vital_signs(pain_score=None)
        assert vital_signs.pain_score is None

    @pytest.mark.parametrize("value", [-1, 11])
    def test_pain_score_outside_range_is_rejected(self, value: int) -> None:
        with pytest.raises(InvalidPainScoreError):
            _make_vital_signs(pain_score=value)

    @pytest.mark.parametrize("value", [0, 10])
    def test_pain_score_at_range_boundary_is_accepted(self, value: int) -> None:
        vital_signs = _make_vital_signs(pain_score=value)
        assert vital_signs.pain_score == value


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        vital_signs = _make_vital_signs()
        vital_signs.pull_events()

        vital_signs.update_details(pulse_bpm=88, pain_score=3)

        assert vital_signs.pulse_bpm == 88
        assert vital_signs.pain_score == 3
        events = vital_signs.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitVitalSignsUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        vital_signs = _make_vital_signs(respiratory_rate=18)
        vital_signs.update_details(pulse_bpm=90)
        assert vital_signs.respiratory_rate == 18

    def test_update_recalculates_bmi(self) -> None:
        vital_signs = _make_vital_signs()
        assert vital_signs.bmi is None

        vital_signs.update_details(height_cm=Decimal("160"), weight_kg=Decimal("50"))

        assert vital_signs.bmi == Decimal("19.5")

    def test_update_with_invalid_temperature_is_rejected(self) -> None:
        vital_signs = _make_vital_signs()
        with pytest.raises(InvalidTemperatureError):
            vital_signs.update_details(temperature_c=Decimal("50.0"))

    def test_update_blood_pressure_replaces_value_object(self) -> None:
        vital_signs = _make_vital_signs()
        new_bp = BloodPressure(systolic=140, diastolic=90)
        vital_signs.update_details(blood_pressure=new_bp)
        assert vital_signs.blood_pressure == new_bp


class TestCalculateBmi:
    def test_none_when_height_missing(self) -> None:
        assert calculate_bmi(height_cm=None, weight_kg=Decimal("70")) is None

    def test_none_when_weight_missing(self) -> None:
        assert calculate_bmi(height_cm=Decimal("170"), weight_kg=None) is None

    def test_none_when_both_missing(self) -> None:
        assert calculate_bmi(height_cm=None, weight_kg=None) is None

    def test_computes_expected_value(self) -> None:
        bmi = calculate_bmi(height_cm=Decimal("170"), weight_kg=Decimal("70"))
        assert bmi == Decimal("24.2")

    def test_rounds_half_up_at_one_decimal_place(self) -> None:
        """200cm / 97kg -> an exact 24.25, the boundary case for
        confirming the rounding mode is `ROUND_HALF_UP` (24.3), not
        banker's rounding (which would give 24.2)."""
        bmi = calculate_bmi(height_cm=Decimal("200"), weight_kg=Decimal("97.0"))
        assert bmi == Decimal("24.3")
