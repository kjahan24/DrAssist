"""Unit tests for the shared NEWS2 per-parameter point functions
(`infrastructure/clinical_scoring/news2_parameters.py`) — the Royal
College of Physicians NEWS2 chart, verified boundary-by-boundary."""

import pytest

from app.modules.risk_stratification_ai.domain.enums import ConsciousnessLevel
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    consciousness_points,
    heart_rate_points,
    oxygen_saturation_points,
    respiratory_rate_points,
    systolic_bp_points,
    temperature_points,
)


class TestRespiratoryRatePoints:
    @pytest.mark.parametrize(
        ("respiratory_rate", "expected_points"),
        [(3, 3), (8, 3), (9, 1), (11, 1), (12, 0), (20, 0), (21, 2), (24, 2), (25, 3), (40, 3)],
    )
    def test_points(self, respiratory_rate: int, expected_points: int) -> None:
        points, _label = respiratory_rate_points(respiratory_rate)
        assert points == expected_points


class TestOxygenSaturationPoints:
    @pytest.mark.parametrize(
        ("oxygen_saturation", "expected_points"),
        [(85.0, 3), (91.0, 3), (92.0, 2), (93.0, 2), (94.0, 1), (95.0, 1), (96.0, 0), (100.0, 0)],
    )
    def test_points(self, oxygen_saturation: float, expected_points: int) -> None:
        points, _label = oxygen_saturation_points(oxygen_saturation)
        assert points == expected_points


class TestSystolicBpPoints:
    @pytest.mark.parametrize(
        ("systolic_bp", "expected_points"),
        [
            (70, 3),
            (90, 3),
            (91, 2),
            (100, 2),
            (101, 1),
            (110, 1),
            (111, 0),
            (219, 0),
            (220, 3),
            (250, 3),
        ],
    )
    def test_points(self, systolic_bp: int, expected_points: int) -> None:
        points, _label = systolic_bp_points(systolic_bp)
        assert points == expected_points


class TestHeartRatePoints:
    @pytest.mark.parametrize(
        ("heart_rate", "expected_points"),
        [
            (30, 3),
            (40, 3),
            (41, 1),
            (50, 1),
            (51, 0),
            (90, 0),
            (91, 1),
            (110, 1),
            (111, 2),
            (130, 2),
            (131, 3),
            (150, 3),
        ],
    )
    def test_points(self, heart_rate: int, expected_points: int) -> None:
        points, _label = heart_rate_points(heart_rate)
        assert points == expected_points


class TestTemperaturePoints:
    @pytest.mark.parametrize(
        ("temperature_celsius", "expected_points"),
        [
            (34.0, 3),
            (35.0, 3),
            (35.1, 1),
            (36.0, 1),
            (36.1, 0),
            (38.0, 0),
            (38.1, 1),
            (39.0, 1),
            (39.1, 2),
            (40.0, 2),
        ],
    )
    def test_points(self, temperature_celsius: float, expected_points: int) -> None:
        points, _label = temperature_points(temperature_celsius)
        assert points == expected_points


class TestConsciousnessPoints:
    def test_alert_is_zero_points(self) -> None:
        points, _label = consciousness_points(ConsciousnessLevel.ALERT)
        assert points == 0

    @pytest.mark.parametrize(
        "level",
        [ConsciousnessLevel.VOICE, ConsciousnessLevel.PAIN, ConsciousnessLevel.UNRESPONSIVE],
    )
    def test_not_alert_is_three_points(self, level: ConsciousnessLevel) -> None:
        points, _label = consciousness_points(level)
        assert points == 3
