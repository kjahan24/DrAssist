"""Unit tests for `DefaultRiskStratificationAnalysisParser`."""

import json

import pytest

from app.modules.risk_stratification_ai.domain.enums import (
    OverallRiskLevel,
    RiskCategory,
    RiskStratificationOutputFormat,
)
from app.modules.risk_stratification_ai.domain.exceptions import (
    InvalidRiskStratificationResponseFormatError,
)
from app.modules.risk_stratification_ai.domain.value_objects import RiskStratificationResult
from app.modules.risk_stratification_ai.infrastructure.parsing.risk_stratification_parser import (
    DefaultRiskStratificationAnalysisParser,
)

_PARSER = DefaultRiskStratificationAnalysisParser()


def _parse(payload: dict[str, object]) -> RiskStratificationResult:
    return _PARSER.parse(json.dumps(payload), output_format=RiskStratificationOutputFormat.JSON)


class TestParseHappyPath:
    def test_parses_a_full_well_formed_payload(self) -> None:
        result = _parse(
            {
                "overall_risk_level": "high",
                "risk_scores": [
                    {
                        "category": "news2",
                        "score_value": 6.0,
                        "contributing_factors": ["Tachycardia", "Hypoxia"],
                        "clinical_explanation": "NEWS2 score of 6.",
                    }
                ],
                "early_warning_indicators": ["SpO2 88% (low)"],
                "recommended_monitoring": ["Continuous SpO2 monitoring"],
                "suggested_escalation": ["Urgent clinician review"],
                "suggested_follow_up": ["Reassess in 1 hour"],
                "red_flag_alerts": ["Hypoxia"],
                "clinical_reasoning": "Grounded in the reported vital signs.",
                "confidence_score": 0.9,
            }
        )

        assert result.overall_risk_level is OverallRiskLevel.HIGH
        assert result.risk_scores[0].category is RiskCategory.NEWS2
        assert result.risk_scores[0].score_value == 6.0
        assert result.risk_scores[0].contributing_factors == ("Tachycardia", "Hypoxia")
        assert result.early_warning_indicators == ("SpO2 88% (low)",)
        assert result.recommended_monitoring == ("Continuous SpO2 monitoring",)
        assert result.suggested_escalation == ("Urgent clinician review",)
        assert result.suggested_follow_up == ("Reassess in 1 hour",)
        assert result.red_flag_alerts == ("Hypoxia",)
        assert result.clinical_reasoning == "Grounded in the reported vital signs."
        assert result.confidence_score == 0.9


class TestParseMalformedJSON:
    def test_raises_when_the_raw_text_is_not_json(self) -> None:
        with pytest.raises(InvalidRiskStratificationResponseFormatError):
            _PARSER.parse("not json at all", output_format=RiskStratificationOutputFormat.JSON)

    def test_strips_markdown_code_fences(self) -> None:
        raw = '```json\n{"overall_risk_level": "low"}\n```'
        result = _PARSER.parse(raw, output_format=RiskStratificationOutputFormat.JSON)
        assert result.overall_risk_level is OverallRiskLevel.LOW


class TestParseLenientDefaults:
    def test_missing_fields_become_empty_or_none(self) -> None:
        result = _parse({})

        assert result.overall_risk_level is OverallRiskLevel.MODERATE
        assert result.risk_scores == ()
        assert result.early_warning_indicators == ()
        assert result.confidence_score is None
        assert result.clinical_reasoning == ""

    def test_unparseable_overall_risk_level_defaults_to_moderate(self) -> None:
        result = _parse({"overall_risk_level": "not-a-real-level"})
        assert result.overall_risk_level is OverallRiskLevel.MODERATE

    def test_unparseable_category_defaults_to_general_clinical_deterioration(self) -> None:
        result = _parse(
            {"risk_scores": [{"category": "not-a-real-category", "clinical_explanation": "x"}]}
        )
        assert result.risk_scores[0].category is RiskCategory.GENERAL_CLINICAL_DETERIORATION

    def test_missing_score_value_becomes_none(self) -> None:
        result = _parse({"risk_scores": [{"category": "news2"}]})
        assert result.risk_scores[0].score_value is None

    def test_non_numeric_score_value_becomes_none(self) -> None:
        result = _parse({"risk_scores": [{"category": "news2", "score_value": "high"}]})
        assert result.risk_scores[0].score_value is None

    def test_non_numeric_confidence_score_becomes_none(self) -> None:
        result = _parse({"confidence_score": "high"})
        assert result.confidence_score is None

    def test_confidence_score_is_not_clamped(self) -> None:
        """Deliberately not clamped — this task's own VALIDATION section
        names "invalid confidence" as its own category, so an
        out-of-range value must survive parsing for the validator to
        reject it."""
        result = _parse({"confidence_score": 5.0})
        assert result.confidence_score == 5.0
        result = _parse({"confidence_score": -5.0})
        assert result.confidence_score == -5.0

    def test_non_list_risk_scores_become_empty_tuple(self) -> None:
        result = _parse({"risk_scores": "not a list"})
        assert result.risk_scores == ()

    def test_missing_contributing_factors_becomes_empty_tuple(self) -> None:
        result = _parse({"risk_scores": [{"category": "news2"}]})
        assert result.risk_scores[0].contributing_factors == ()

    def test_non_string_list_items_are_dropped(self) -> None:
        result = _parse({"red_flag_alerts": ["ok", 5, None, "  "]})
        assert result.red_flag_alerts == ("ok",)

    def test_raw_text_and_output_format_are_preserved(self) -> None:
        raw = json.dumps({"overall_risk_level": "low"})
        result = _PARSER.parse(raw, output_format=RiskStratificationOutputFormat.MARKDOWN)
        assert result.raw_text == raw
        assert result.output_format is RiskStratificationOutputFormat.MARKDOWN
