"""Unit tests for `DefaultDrugSafetyAnalysisParser`."""

import json

import pytest

from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    EvidenceLevel,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.exceptions import (
    InvalidDrugInteractionResponseFormatError,
)
from app.modules.drug_interaction_ai.domain.value_objects import DrugInteractionAnalysisResult
from app.modules.drug_interaction_ai.infrastructure.parsing.drug_safety_analysis_parser import (
    DefaultDrugSafetyAnalysisParser,
)

_PARSER = DefaultDrugSafetyAnalysisParser()


def _parse(payload: dict[str, object]) -> DrugInteractionAnalysisResult:
    return _PARSER.parse(json.dumps(payload), output_format=DrugInteractionOutputFormat.JSON)


class TestParseHappyPath:
    def test_parses_a_full_well_formed_payload(self) -> None:
        result = _parse(
            {
                "safety_summary": "One major interaction identified.",
                "interactions": [
                    {
                        "category": "drug_drug_interaction",
                        "description": "Warfarin and Aspirin",
                        "severity": "major",
                        "mechanism": "Additive anticoagulation",
                        "clinical_significance": "Increased bleeding risk",
                        "evidence_level": "established",
                        "involved_medications": ["Warfarin", "Aspirin"],
                    }
                ],
                "contraindications": ["Do not use with nitrates"],
                "warnings": ["Bleeding risk"],
                "monitoring_recommendations": ["Monitor INR"],
                "dose_adjustment_suggestions": ["Reduce dose"],
                "alternative_medication_suggestions": ["Consider acetaminophen"],
                "patient_counseling_points": ["Report unusual bruising"],
                "confidence_score": 0.9,
                "clinical_reasoning": "Grounded in the reported medication list.",
            }
        )

        assert result.safety_summary == "One major interaction identified."
        assert result.interactions[0].category is SafetyIssueCategory.DRUG_DRUG_INTERACTION
        assert result.interactions[0].severity is SafetySeverity.MAJOR
        assert result.interactions[0].evidence_level is EvidenceLevel.ESTABLISHED
        assert result.interactions[0].involved_medications == ("Warfarin", "Aspirin")
        assert result.contraindications == ("Do not use with nitrates",)
        assert result.warnings == ("Bleeding risk",)
        assert result.monitoring_recommendations == ("Monitor INR",)
        assert result.dose_adjustment_suggestions == ("Reduce dose",)
        assert result.alternative_medication_suggestions == ("Consider acetaminophen",)
        assert result.patient_counseling_points == ("Report unusual bruising",)
        assert result.confidence_score == 0.9
        assert result.clinical_reasoning == "Grounded in the reported medication list."


class TestParseMalformedJSON:
    def test_raises_when_the_raw_text_is_not_json(self) -> None:
        with pytest.raises(InvalidDrugInteractionResponseFormatError):
            _PARSER.parse("not json at all", output_format=DrugInteractionOutputFormat.JSON)

    def test_strips_markdown_code_fences(self) -> None:
        raw = '```json\n{"safety_summary": "ok"}\n```'
        result = _PARSER.parse(raw, output_format=DrugInteractionOutputFormat.JSON)
        assert result.safety_summary == "ok"


class TestParseLenientDefaults:
    def test_missing_fields_become_empty_or_none(self) -> None:
        result = _parse({})

        assert result.safety_summary == ""
        assert result.interactions == ()
        assert result.contraindications == ()
        assert result.confidence_score is None
        assert result.clinical_reasoning == ""

    def test_unparseable_category_defaults_to_drug_drug_interaction(self) -> None:
        result = _parse({"interactions": [{"description": "X", "category": "not-a-real-category"}]})
        assert result.interactions[0].category is SafetyIssueCategory.DRUG_DRUG_INTERACTION

    def test_unparseable_severity_defaults_to_moderate(self) -> None:
        result = _parse({"interactions": [{"description": "X", "severity": "extreme"}]})
        assert result.interactions[0].severity is SafetySeverity.MODERATE

    def test_missing_evidence_level_becomes_none(self) -> None:
        result = _parse({"interactions": [{"description": "X"}]})
        assert result.interactions[0].evidence_level is None

    def test_unparseable_evidence_level_becomes_none(self) -> None:
        result = _parse(
            {"interactions": [{"description": "X", "evidence_level": "not-a-real-level"}]}
        )
        assert result.interactions[0].evidence_level is None

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

    def test_non_list_interactions_become_empty_tuple(self) -> None:
        result = _parse({"interactions": "not a list"})
        assert result.interactions == ()

    def test_missing_mechanism_and_clinical_significance_become_none(self) -> None:
        result = _parse({"interactions": [{"description": "X"}]})
        assert result.interactions[0].mechanism is None
        assert result.interactions[0].clinical_significance is None

    def test_missing_involved_medications_becomes_empty_tuple(self) -> None:
        result = _parse({"interactions": [{"description": "X"}]})
        assert result.interactions[0].involved_medications == ()

    def test_non_string_list_items_are_dropped(self) -> None:
        result = _parse({"contraindications": ["ok", 5, None, "  "]})
        assert result.contraindications == ("ok",)

    def test_raw_text_and_output_format_are_preserved(self) -> None:
        raw = json.dumps({"safety_summary": "ok"})
        result = _PARSER.parse(raw, output_format=DrugInteractionOutputFormat.MARKDOWN)
        assert result.raw_text == raw
        assert result.output_format is DrugInteractionOutputFormat.MARKDOWN
