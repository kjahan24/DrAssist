"""Unit tests for `StandardEarlyWarningAnalyzer`."""

import pytest

from app.modules.risk_stratification_ai.domain.enums import ConsciousnessLevel, RiskCategory
from app.modules.risk_stratification_ai.infrastructure.early_warning.standard_early_warning_analyzer import (  # noqa: E501
    StandardEarlyWarningAnalyzer,
)
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    make_risk_score,
    make_vital_signs,
)

_ANALYZER = StandardEarlyWarningAnalyzer()

_NORMAL_VITALS: dict[str, object] = {
    "respiratory_rate": 16,
    "oxygen_saturation": 98.0,
    "temperature_celsius": 37.0,
    "systolic_bp": 120,
    "heart_rate": 75,
    "consciousness_level": ConsciousnessLevel.ALERT,
}


class TestIdentifySingleParameterTriggers:
    def test_no_triggers_for_normal_vitals(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        assert _ANALYZER.identify_single_parameter_triggers(vital_signs) == ()

    def test_triggers_for_a_critically_low_respiratory_rate(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["respiratory_rate"] = 5
        vital_signs = make_vital_signs(**kwargs)

        triggers = _ANALYZER.identify_single_parameter_triggers(vital_signs)

        assert len(triggers) == 1
        assert "Respiratory rate" in triggers[0]

    def test_triggers_for_severely_low_oxygen_saturation(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["oxygen_saturation"] = 88.0
        vital_signs = make_vital_signs(**kwargs)

        triggers = _ANALYZER.identify_single_parameter_triggers(vital_signs)

        assert any("SpO2" in trigger for trigger in triggers)

    def test_triggers_for_extreme_systolic_bp(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["systolic_bp"] = 85
        vital_signs = make_vital_signs(**kwargs)

        triggers = _ANALYZER.identify_single_parameter_triggers(vital_signs)

        assert any("Systolic BP" in trigger for trigger in triggers)

    def test_triggers_for_extreme_heart_rate(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["heart_rate"] = 35
        vital_signs = make_vital_signs(**kwargs)

        triggers = _ANALYZER.identify_single_parameter_triggers(vital_signs)

        assert any("Heart rate" in trigger for trigger in triggers)

    def test_triggers_for_extreme_temperature(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["temperature_celsius"] = 34.0
        vital_signs = make_vital_signs(**kwargs)

        triggers = _ANALYZER.identify_single_parameter_triggers(vital_signs)

        assert any("Temperature" in trigger for trigger in triggers)

    def test_triggers_for_altered_consciousness(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["consciousness_level"] = ConsciousnessLevel.UNRESPONSIVE
        vital_signs = make_vital_signs(**kwargs)

        triggers = _ANALYZER.identify_single_parameter_triggers(vital_signs)

        assert any("Not alert" in trigger for trigger in triggers)

    def test_multiple_triggers_can_fire_simultaneously(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs.update(respiratory_rate=5, oxygen_saturation=88.0)
        vital_signs = make_vital_signs(**kwargs)

        triggers = _ANALYZER.identify_single_parameter_triggers(vital_signs)

        assert len(triggers) == 2

    def test_missing_parameters_do_not_trigger(self) -> None:
        vital_signs = make_vital_signs(respiratory_rate=16)
        assert _ANALYZER.identify_single_parameter_triggers(vital_signs) == ()


class TestClassifyEscalationUrgency:
    def test_returns_none_when_score_value_is_none(self) -> None:
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=None)
        assert _ANALYZER.classify_escalation_urgency(score) is None

    def test_returns_none_for_a_category_with_no_escalation_mapping(self) -> None:
        score = make_risk_score(category=RiskCategory.FALL_RISK, score_value=0.5)
        assert _ANALYZER.classify_escalation_urgency(score) is None

    @pytest.mark.parametrize(
        ("score_value", "expects_none"),
        [(0.0, True), (4.0, False), (6.0, False), (9.0, False)],
    )
    def test_news2_escalation(self, score_value: float, expects_none: bool) -> None:
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=score_value)
        result = _ANALYZER.classify_escalation_urgency(score)
        assert (result is None) is expects_none

    def test_news2_critical_mentions_immediate_escalation(self) -> None:
        score = make_risk_score(category=RiskCategory.NEWS2, score_value=8.0)
        result = _ANALYZER.classify_escalation_urgency(score)
        assert result is not None
        assert "Immediate" in result

    @pytest.mark.parametrize(
        ("score_value", "expects_none"), [(0.0, True), (2.0, True), (3.0, False), (5.0, False)]
    )
    def test_mews_escalation(self, score_value: float, expects_none: bool) -> None:
        score = make_risk_score(category=RiskCategory.MEWS, score_value=score_value)
        result = _ANALYZER.classify_escalation_urgency(score)
        assert (result is None) is expects_none

    @pytest.mark.parametrize(
        ("score_value", "expects_none"), [(0.0, True), (1.0, True), (2.0, False), (3.0, False)]
    )
    def test_qsofa_escalation(self, score_value: float, expects_none: bool) -> None:
        score = make_risk_score(category=RiskCategory.QSOFA, score_value=score_value)
        result = _ANALYZER.classify_escalation_urgency(score)
        assert (result is None) is expects_none

    @pytest.mark.parametrize(
        ("score_value", "expects_none"),
        [(0.0, True), (2.0, True), (3.0, False), (5.0, False)],
    )
    def test_sofa_simplified_escalation(self, score_value: float, expects_none: bool) -> None:
        score = make_risk_score(category=RiskCategory.SOFA_SIMPLIFIED, score_value=score_value)
        result = _ANALYZER.classify_escalation_urgency(score)
        assert (result is None) is expects_none
