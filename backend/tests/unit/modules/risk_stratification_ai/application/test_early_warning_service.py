"""Tests for `EarlyWarningService`."""

import pytest

from app.modules.risk_stratification_ai.application.services.early_warning_service import (
    EarlyWarningService,
)
from app.modules.risk_stratification_ai.domain.enums import OverallRiskLevel, RiskCategory
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    FakeEarlyWarningPort,
    make_risk_score,
    make_vital_signs,
)


class TestIdentifyEarlyWarningIndicators:
    def test_delegates_to_port(self) -> None:
        port = FakeEarlyWarningPort(triggers=("Single-parameter trigger: SpO2 88% (low)",))
        service = EarlyWarningService(early_warning_port=port)

        result = service.identify_early_warning_indicators(make_vital_signs())

        assert result == ("Single-parameter trigger: SpO2 88% (low)",)
        assert port.trigger_calls == [make_vital_signs()]

    def test_empty_when_port_returns_no_triggers(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        assert service.identify_early_warning_indicators(make_vital_signs()) == ()


class TestIdentifyRedFlags:
    def test_includes_single_parameter_triggers(self) -> None:
        port = FakeEarlyWarningPort(triggers=("Single-parameter trigger: HR 145/min",))
        service = EarlyWarningService(early_warning_port=port)

        result = service.identify_red_flags(make_vital_signs(), ())

        assert "Single-parameter trigger: HR 145/min" in result

    def test_adds_flag_for_critical_news2_score(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=8.0)

        result = service.identify_red_flags(make_vital_signs(), (score,))

        assert any("news2" in flag for flag in result)

    def test_no_flag_for_non_critical_news2_score(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=2.0)

        result = service.identify_red_flags(make_vital_signs(), (score,))

        assert result == ()

    def test_no_flag_when_score_value_is_none(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=None)

        result = service.identify_red_flags(make_vital_signs(), (score,))

        assert result == ()

    def test_no_flag_for_unrecognized_category(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.FALL_RISK, score_value=0.9)

        result = service.identify_red_flags(make_vital_signs(), (score,))

        assert result == ()


class TestDetermineMinimumRiskLevel:
    def test_returns_none_when_no_standardized_scores_present(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=None)

        assert service.determine_minimum_risk_level((score,)) is None

    def test_returns_none_for_empty_risk_scores(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        assert service.determine_minimum_risk_level(()) is None

    @pytest.mark.parametrize(
        ("score_value", "expected"),
        [
            (0.0, OverallRiskLevel.LOW),
            (1.0, OverallRiskLevel.MODERATE),
            (4.0, OverallRiskLevel.MODERATE),
            (5.0, OverallRiskLevel.HIGH),
            (6.0, OverallRiskLevel.HIGH),
            (7.0, OverallRiskLevel.CRITICAL),
            (20.0, OverallRiskLevel.CRITICAL),
        ],
    )
    def test_news2_thresholds(self, score_value: float, expected: OverallRiskLevel) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=score_value)

        assert service.determine_minimum_risk_level((score,)) is expected

    @pytest.mark.parametrize(
        ("score_value", "expected"),
        [
            (0.0, OverallRiskLevel.LOW),
            (2.0, OverallRiskLevel.LOW),
            (3.0, OverallRiskLevel.MODERATE),
            (4.0, OverallRiskLevel.MODERATE),
            (5.0, OverallRiskLevel.HIGH),
            (14.0, OverallRiskLevel.HIGH),
        ],
    )
    def test_mews_thresholds(self, score_value: float, expected: OverallRiskLevel) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.MEWS, score_value=score_value)

        assert service.determine_minimum_risk_level((score,)) is expected

    @pytest.mark.parametrize(
        ("score_value", "expected"),
        [
            (0.0, OverallRiskLevel.LOW),
            (1.0, OverallRiskLevel.LOW),
            (2.0, OverallRiskLevel.HIGH),
            (3.0, OverallRiskLevel.HIGH),
        ],
    )
    def test_qsofa_thresholds(self, score_value: float, expected: OverallRiskLevel) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.QSOFA, score_value=score_value)

        assert service.determine_minimum_risk_level((score,)) is expected

    @pytest.mark.parametrize(
        ("score_value", "expected"),
        [
            (0.0, OverallRiskLevel.LOW),
            (1.0, OverallRiskLevel.MODERATE),
            (2.0, OverallRiskLevel.MODERATE),
            (3.0, OverallRiskLevel.HIGH),
            (4.0, OverallRiskLevel.HIGH),
            (5.0, OverallRiskLevel.CRITICAL),
            (8.0, OverallRiskLevel.CRITICAL),
        ],
    )
    def test_sofa_simplified_thresholds(
        self, score_value: float, expected: OverallRiskLevel
    ) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.SOFA_SIMPLIFIED, score_value=score_value)

        assert service.determine_minimum_risk_level((score,)) is expected

    def test_takes_the_maximum_across_multiple_standardized_scores(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        low_news2 = make_risk_score(category=RiskCategory.NEWS2, score_value=0.0)
        high_qsofa = make_risk_score(category=RiskCategory.QSOFA, score_value=2.0)

        result = service.determine_minimum_risk_level((low_news2, high_qsofa))

        assert result is OverallRiskLevel.HIGH


class TestApplyDeterministicFloor:
    def test_returns_ai_reported_when_no_floor_computed(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=None)

        result = service.apply_deterministic_floor(OverallRiskLevel.LOW, (score,))

        assert result is OverallRiskLevel.LOW

    def test_floor_raises_a_lower_ai_reported_level(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=8.0)

        result = service.apply_deterministic_floor(OverallRiskLevel.LOW, (score,))

        assert result is OverallRiskLevel.CRITICAL

    def test_higher_ai_reported_level_is_preserved(self) -> None:
        service = EarlyWarningService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=1.0)

        result = service.apply_deterministic_floor(OverallRiskLevel.CRITICAL, (score,))

        assert result is OverallRiskLevel.CRITICAL
