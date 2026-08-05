"""Unit tests for `StandardRiskScoringCalculator` — NEWS2, MEWS, qSOFA,
and simplified-SOFA computation, per this task's own explicit "NEWS2
tests, MEWS tests, qSOFA tests" TESTS requirement."""

import pytest

from app.modules.risk_stratification_ai.domain.enums import ConsciousnessLevel, RiskCategory
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.standard_risk_scoring_calculator import (  # noqa: E501
    StandardRiskScoringCalculator,
)
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    make_lab_value,
    make_vital_signs,
)

_CALCULATOR = StandardRiskScoringCalculator()

_NORMAL_VITALS: dict[str, object] = {
    "respiratory_rate": 14,
    "oxygen_saturation": 98.0,
    "on_supplemental_oxygen": False,
    "temperature_celsius": 37.0,
    "systolic_bp": 120,
    "diastolic_bp": 80,
    "heart_rate": 75,
    "consciousness_level": ConsciousnessLevel.ALERT,
}


class TestComputeNews2:
    @pytest.mark.parametrize(
        "missing_field",
        [
            "respiratory_rate",
            "oxygen_saturation",
            "systolic_bp",
            "heart_rate",
            "temperature_celsius",
            "consciousness_level",
        ],
    )
    def test_returns_none_when_a_required_field_is_missing(self, missing_field: str) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs[missing_field] = None
        vital_signs = make_vital_signs(**kwargs)

        assert _CALCULATOR.compute_news2(vital_signs) is None

    def test_normal_vitals_score_zero(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        score = _CALCULATOR.compute_news2(vital_signs)

        assert score is not None
        assert score.category is RiskCategory.NEWS2
        assert score.score_value == 0.0
        assert score.contributing_factors == ()

    def test_severely_abnormal_vitals_score_high(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs.update(
            respiratory_rate=6,
            oxygen_saturation=88.0,
            on_supplemental_oxygen=True,
            temperature_celsius=34.5,
            systolic_bp=85,
            heart_rate=140,
            consciousness_level=ConsciousnessLevel.PAIN,
        )
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_news2(vital_signs)

        assert score is not None
        assert score.score_value == pytest.approx(20.0)

    def test_supplemental_oxygen_adds_two_points(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["on_supplemental_oxygen"] = True
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_news2(vital_signs)

        assert score is not None
        assert score.score_value == 2.0

    def test_none_supplemental_oxygen_is_treated_as_room_air(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["on_supplemental_oxygen"] = None
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_news2(vital_signs)

        assert score is not None
        assert score.score_value == 0.0

    def test_contributing_factors_only_include_nonzero_components(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["respiratory_rate"] = 22
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_news2(vital_signs)

        assert score is not None
        assert len(score.contributing_factors) == 1
        assert "Respiratory rate" in score.contributing_factors[0]

    def test_explanation_mentions_news2(self) -> None:
        score = _CALCULATOR.compute_news2(make_vital_signs(**_NORMAL_VITALS))
        assert score is not None
        assert "NEWS2" in score.clinical_explanation


class TestComputeMews:
    @pytest.mark.parametrize(
        "missing_field",
        [
            "systolic_bp",
            "heart_rate",
            "respiratory_rate",
            "temperature_celsius",
            "consciousness_level",
        ],
    )
    def test_returns_none_when_a_required_field_is_missing(self, missing_field: str) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs[missing_field] = None
        vital_signs = make_vital_signs(**kwargs)

        assert _CALCULATOR.compute_mews(vital_signs) is None

    def test_does_not_require_oxygen_saturation(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["oxygen_saturation"] = None
        vital_signs = make_vital_signs(**kwargs)

        assert _CALCULATOR.compute_mews(vital_signs) is not None

    def test_normal_vitals_score_zero(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        score = _CALCULATOR.compute_mews(vital_signs)

        assert score is not None
        assert score.category is RiskCategory.MEWS
        assert score.score_value == 0.0

    def test_abnormal_vitals_score_high(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs.update(
            systolic_bp=65,
            heart_rate=135,
            respiratory_rate=32,
            temperature_celsius=39.0,
            consciousness_level=ConsciousnessLevel.UNRESPONSIVE,
        )
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_mews(vital_signs)

        assert score is not None
        assert score.score_value == pytest.approx(14.0)

    def test_explanation_mentions_mews(self) -> None:
        score = _CALCULATOR.compute_mews(make_vital_signs(**_NORMAL_VITALS))
        assert score is not None
        assert "MEWS" in score.clinical_explanation


class TestComputeQsofa:
    @pytest.mark.parametrize(
        "missing_field", ["respiratory_rate", "systolic_bp", "consciousness_level"]
    )
    def test_returns_none_when_a_required_field_is_missing(self, missing_field: str) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs[missing_field] = None
        vital_signs = make_vital_signs(**kwargs)

        assert _CALCULATOR.compute_qsofa(vital_signs) is None

    def test_normal_vitals_score_zero(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        score = _CALCULATOR.compute_qsofa(vital_signs)

        assert score is not None
        assert score.category is RiskCategory.QSOFA
        assert score.score_value == 0.0

    def test_high_respiratory_rate_scores_one_point(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["respiratory_rate"] = 22
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_qsofa(vital_signs)

        assert score is not None
        assert score.score_value == 1.0

    def test_low_systolic_bp_scores_one_point(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["systolic_bp"] = 95
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_qsofa(vital_signs)

        assert score is not None
        assert score.score_value == 1.0

    def test_altered_mentation_scores_one_point(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["consciousness_level"] = ConsciousnessLevel.VOICE
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_qsofa(vital_signs)

        assert score is not None
        assert score.score_value == 1.0

    def test_all_three_criteria_score_three_points(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs.update(
            respiratory_rate=25,
            systolic_bp=90,
            consciousness_level=ConsciousnessLevel.PAIN,
        )
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_qsofa(vital_signs)

        assert score is not None
        assert score.score_value == 3.0

    def test_respiratory_rate_boundary_of_22_is_included(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs["respiratory_rate"] = 21
        vital_signs = make_vital_signs(**kwargs)

        score = _CALCULATOR.compute_qsofa(vital_signs)

        assert score is not None
        assert score.score_value == 0.0

    def test_explanation_mentions_qsofa(self) -> None:
        score = _CALCULATOR.compute_qsofa(make_vital_signs(**_NORMAL_VITALS))
        assert score is not None
        assert "qSOFA" in score.clinical_explanation


class TestComputeSofaSimplified:
    @pytest.mark.parametrize(
        "missing_field", ["oxygen_saturation", "systolic_bp", "consciousness_level"]
    )
    def test_returns_none_when_a_required_field_is_missing(self, missing_field: str) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs[missing_field] = None
        vital_signs = make_vital_signs(**kwargs)

        assert _CALCULATOR.compute_sofa_simplified(vital_signs, ()) is None

    def test_does_not_require_lab_values(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        score = _CALCULATOR.compute_sofa_simplified(vital_signs, ())

        assert score is not None
        assert score.category is RiskCategory.SOFA_SIMPLIFIED

    def test_normal_vitals_score_zero_without_labs(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        score = _CALCULATOR.compute_sofa_simplified(vital_signs, ())

        assert score is not None
        assert score.score_value == 0.0

    def test_elevated_creatinine_adds_renal_points(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        lab_values = (make_lab_value(test_name="Creatinine", numeric_value=2.5),)

        score = _CALCULATOR.compute_sofa_simplified(vital_signs, lab_values)

        assert score is not None
        assert score.score_value == 2.0

    def test_normal_creatinine_adds_no_renal_points(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        lab_values = (make_lab_value(test_name="Creatinine", numeric_value=0.8),)

        score = _CALCULATOR.compute_sofa_simplified(vital_signs, lab_values)

        assert score is not None
        assert score.score_value == 0.0

    def test_non_creatinine_lab_values_are_ignored(self) -> None:
        vital_signs = make_vital_signs(**_NORMAL_VITALS)
        lab_values = (make_lab_value(test_name="Hemoglobin", numeric_value=8.0),)

        score = _CALCULATOR.compute_sofa_simplified(vital_signs, lab_values)

        assert score is not None
        assert score.score_value == 0.0

    def test_severely_abnormal_vitals_and_labs_score_high(self) -> None:
        kwargs = dict(_NORMAL_VITALS)
        kwargs.update(
            oxygen_saturation=85.0,
            systolic_bp=80,
            consciousness_level=ConsciousnessLevel.UNRESPONSIVE,
        )
        vital_signs = make_vital_signs(**kwargs)
        lab_values = (make_lab_value(test_name="Creatinine", numeric_value=3.0),)

        score = _CALCULATOR.compute_sofa_simplified(vital_signs, lab_values)

        assert score is not None
        assert score.score_value == pytest.approx(8.0)

    def test_explanation_documents_the_simplification(self) -> None:
        score = _CALCULATOR.compute_sofa_simplified(make_vital_signs(**_NORMAL_VITALS), ())
        assert score is not None
        assert "simplified" in score.clinical_explanation.lower()
        assert "PaO2/FiO2" in score.clinical_explanation
