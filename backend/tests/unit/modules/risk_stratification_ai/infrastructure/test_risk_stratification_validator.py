"""Unit tests for `DefaultRiskStratificationAnalysisValidator`."""

import pytest

from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.exceptions import (
    HallucinatedRiskFactorError,
    InvalidRiskConfidenceValueError,
    InvalidRiskScoreError,
)
from app.modules.risk_stratification_ai.infrastructure.validation.risk_stratification_validator import (  # noqa: E501
    DefaultRiskStratificationAnalysisValidator,
)
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    make_input,
    make_result,
    make_risk_score,
)


def _validator() -> DefaultRiskStratificationAnalysisValidator:
    return DefaultRiskStratificationAnalysisValidator()


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        _validator().validate(make_result(), make_input())


class TestValidateInvalidScores:
    @pytest.mark.parametrize(
        ("category", "score_value"),
        [
            (RiskCategory.NEWS2, -1.0),
            (RiskCategory.NEWS2, 21.0),
            (RiskCategory.MEWS, -1.0),
            (RiskCategory.MEWS, 15.0),
            (RiskCategory.QSOFA, -1.0),
            (RiskCategory.QSOFA, 4.0),
            (RiskCategory.SOFA_SIMPLIFIED, -1.0),
            (RiskCategory.SOFA_SIMPLIFIED, 9.0),
        ],
    )
    def test_raises_for_out_of_range_standardized_scores(
        self, category: RiskCategory, score_value: float
    ) -> None:
        score = make_risk_score(category=category, score_value=score_value)
        result = make_result(risk_scores=(score,))

        with pytest.raises(InvalidRiskScoreError):
            _validator().validate(result, make_input())

    @pytest.mark.parametrize(
        ("category", "score_value"),
        [
            (RiskCategory.NEWS2, 0.0),
            (RiskCategory.NEWS2, 20.0),
            (RiskCategory.MEWS, 0.0),
            (RiskCategory.MEWS, 14.0),
            (RiskCategory.QSOFA, 0.0),
            (RiskCategory.QSOFA, 3.0),
            (RiskCategory.SOFA_SIMPLIFIED, 0.0),
            (RiskCategory.SOFA_SIMPLIFIED, 8.0),
        ],
    )
    def test_accepts_boundary_standardized_scores(
        self, category: RiskCategory, score_value: float
    ) -> None:
        score = make_risk_score(category=category, score_value=score_value)
        result = make_result(risk_scores=(score,))
        _validator().validate(result, make_input())

    def test_accepts_a_none_score_value_for_any_category(self) -> None:
        result = make_result(
            risk_scores=(make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=None),)
        )
        _validator().validate(result, make_input())

    @pytest.mark.parametrize("score_value", [-0.1, 1.1])
    def test_raises_for_out_of_range_qualitative_scores(self, score_value: float) -> None:
        result = make_result(
            risk_scores=(
                make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=score_value),
            )
        )
        with pytest.raises(InvalidRiskScoreError):
            _validator().validate(result, make_input())

    @pytest.mark.parametrize("score_value", [0.0, 0.5, 1.0])
    def test_accepts_in_range_qualitative_scores(self, score_value: float) -> None:
        result = make_result(
            risk_scores=(
                make_risk_score(category=RiskCategory.SEPSIS_RISK, score_value=score_value),
            )
        )
        _validator().validate(result, make_input())


class TestValidateInvalidConfidenceValues:
    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_confidence_is_out_of_range(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)

        with pytest.raises(InvalidRiskConfidenceValueError):
            _validator().validate(result, make_input())

    def test_accepts_a_none_confidence_value(self) -> None:
        result = make_result(confidence_score=None)
        _validator().validate(result, make_input())

    @pytest.mark.parametrize("confidence_score", [0.0, 1.0, 0.5])
    def test_accepts_boundary_valid_confidence_scores(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)
        _validator().validate(result, make_input())


class TestValidateHallucinatedPlaceholders:
    @pytest.mark.parametrize(
        "placeholder",
        [
            "[insert reasoning here]",
            "[PLACEHOLDER]",
            "<insert findings>",
            "TBD",
            "TODO",
            "XXX",
            "Lorem ipsum dolor sit amet",
        ],
    )
    def test_raises_when_clinical_reasoning_contains_a_placeholder(self, placeholder: str) -> None:
        result = make_result(clinical_reasoning=f"Reasoning: {placeholder}")

        with pytest.raises(HallucinatedRiskFactorError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "clinical_reasoning"

    def test_raises_when_a_risk_score_clinical_explanation_contains_a_placeholder(self) -> None:
        result = make_result(
            risk_scores=(make_risk_score(clinical_explanation="[insert explanation]"),)
        )

        with pytest.raises(HallucinatedRiskFactorError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "risk_scores"

    def test_raises_when_a_risk_score_contributing_factor_contains_a_placeholder(self) -> None:
        result = make_result(risk_scores=(make_risk_score(contributing_factors=("TBD",)),))

        with pytest.raises(HallucinatedRiskFactorError):
            _validator().validate(result, make_input())

    def test_raises_when_early_warning_indicators_contains_a_placeholder(self) -> None:
        result = make_result(early_warning_indicators=("[insert indicator]",))

        with pytest.raises(HallucinatedRiskFactorError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "early_warning_indicators"

    def test_raises_when_recommended_monitoring_contains_a_placeholder(self) -> None:
        result = make_result(recommended_monitoring=("TBD",))

        with pytest.raises(HallucinatedRiskFactorError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "recommended_monitoring"

    def test_raises_when_suggested_escalation_contains_a_placeholder(self) -> None:
        result = make_result(suggested_escalation=("TBD",))

        with pytest.raises(HallucinatedRiskFactorError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "suggested_escalation"

    def test_raises_when_suggested_follow_up_contains_a_placeholder(self) -> None:
        result = make_result(suggested_follow_up=("TBD",))

        with pytest.raises(HallucinatedRiskFactorError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "suggested_follow_up"

    def test_raises_when_red_flag_alerts_contains_a_placeholder(self) -> None:
        result = make_result(red_flag_alerts=("TBD",))

        with pytest.raises(HallucinatedRiskFactorError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "red_flag_alerts"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        _validator().validate(make_result(), make_input())


class TestValidateCheckOrdering:
    def test_invalid_score_is_checked_before_confidence_value(self) -> None:
        result = make_result(
            risk_scores=(make_risk_score(category=RiskCategory.NEWS2, score_value=99.0),),
            confidence_score=5.0,
        )

        with pytest.raises(InvalidRiskScoreError):
            _validator().validate(result, make_input())
