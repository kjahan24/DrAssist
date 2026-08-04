"""Unit tests for `DefaultMedicalReasoningParser`."""

import json

import pytest

from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    RedFlagPriority,
)
from app.modules.medical_reasoning_ai.domain.exceptions import (
    InvalidMedicalReasoningResponseFormatError,
)
from app.modules.medical_reasoning_ai.infrastructure.parsing.medical_reasoning_parser import (
    DefaultMedicalReasoningParser,
)

_VALID_PAYLOAD = {
    "clinical_summary": "Patient presents with chest pain.",
    "evidence": [
        {"description": "Elevated troponin", "weight": 0.8, "polarity": "supporting"},
        {"description": "No ECG changes", "weight": 0.4, "polarity": "contradicting"},
    ],
    "missing_information": ["No imaging provided"],
    "clinical_confidence": 0.7,
    "diagnostic_confidence": 0.6,
    "therapeutic_confidence": 0.5,
    "risk_factors": ["Hypertension"],
    "red_flags": [{"description": "Hypotension", "priority": "critical"}],
    "suggested_next_questions": ["Any recent travel?"],
    "suggested_investigations": ["ECG"],
    "suggested_monitoring": ["Repeat troponin in 6 hours"],
    "clinical_justification": "Grounded in the elevated troponin.",
}


class TestParsePlainJSON:
    def test_parses_the_clinical_summary_and_justification(self) -> None:
        parser = DefaultMedicalReasoningParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=MedicalReasoningOutputFormat.JSON
        )

        assert result.clinical_summary == "Patient presents with chest pain."
        assert result.clinical_justification == "Grounded in the elevated troponin."

    def test_parses_evidence_items(self) -> None:
        parser = DefaultMedicalReasoningParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=MedicalReasoningOutputFormat.JSON
        )

        assert len(result.evidence) == 2
        assert result.evidence[0].description == "Elevated troponin"
        assert result.evidence[0].weight == 0.8
        assert result.evidence[0].polarity is EvidencePolarity.SUPPORTING
        assert result.evidence[1].polarity is EvidencePolarity.CONTRADICTING

    def test_parses_confidence_values(self) -> None:
        parser = DefaultMedicalReasoningParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=MedicalReasoningOutputFormat.JSON
        )

        assert result.clinical_confidence == 0.7
        assert result.diagnostic_confidence == 0.6
        assert result.therapeutic_confidence == 0.5

    def test_parses_red_flags(self) -> None:
        parser = DefaultMedicalReasoningParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=MedicalReasoningOutputFormat.JSON
        )

        assert result.red_flags[0].description == "Hypotension"
        assert result.red_flags[0].priority is RedFlagPriority.CRITICAL

    def test_parses_recommendation_lists(self) -> None:
        parser = DefaultMedicalReasoningParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=MedicalReasoningOutputFormat.JSON
        )

        assert result.suggested_next_questions == ("Any recent travel?",)
        assert result.suggested_investigations == ("ECG",)
        assert result.suggested_monitoring == ("Repeat troponin in 6 hours",)

    def test_carries_through_the_requested_output_format(self) -> None:
        parser = DefaultMedicalReasoningParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=MedicalReasoningOutputFormat.MARKDOWN
        )

        assert result.output_format is MedicalReasoningOutputFormat.MARKDOWN

    def test_preserves_the_original_raw_text(self) -> None:
        parser = DefaultMedicalReasoningParser()
        raw_text = json.dumps(_VALID_PAYLOAD)

        result = parser.parse(raw_text, output_format=MedicalReasoningOutputFormat.JSON)

        assert result.raw_text == raw_text

    def test_missing_optional_top_level_keys_default_to_empty(self) -> None:
        parser = DefaultMedicalReasoningParser()

        result = parser.parse(
            json.dumps({"clinical_summary": "x"}), output_format=MedicalReasoningOutputFormat.JSON
        )

        assert result.evidence == ()
        assert result.red_flags == ()
        assert result.missing_information == ()
        assert result.clinical_confidence is None


class TestParseFencedJSON:
    def test_parses_json_wrapped_in_a_labeled_fence(self) -> None:
        parser = DefaultMedicalReasoningParser()
        raw = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"

        result = parser.parse(raw, output_format=MedicalReasoningOutputFormat.JSON)

        assert result.clinical_summary == "Patient presents with chest pain."

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = DefaultMedicalReasoningParser()
        raw = f"```\n{json.dumps(_VALID_PAYLOAD)}\n```"

        result = parser.parse(raw, output_format=MedicalReasoningOutputFormat.JSON)

        assert result.clinical_justification == "Grounded in the elevated troponin."


class TestParseMissingOrMalformedFields:
    def test_missing_fields_in_an_evidence_item_become_empty_or_defaulted(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {"clinical_summary": "x", "evidence": [{"description": "Fever"}]}

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert result.evidence[0].description == "Fever"
        assert result.evidence[0].weight == 0.5
        assert result.evidence[0].polarity is EvidencePolarity.SUPPORTING

    def test_a_boolean_weight_is_not_treated_as_a_number(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {
            "clinical_summary": "x",
            "evidence": [{"description": "Fever", "weight": True}],
        }

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert result.evidence[0].weight == 0.5

    def test_a_boolean_confidence_score_is_not_treated_as_a_number(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {"clinical_summary": "x", "clinical_confidence": True}

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert result.clinical_confidence is None

    def test_an_unrecognized_polarity_defaults_to_supporting(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {
            "clinical_summary": "x",
            "evidence": [{"description": "Fever", "polarity": "neutral"}],
        }

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert result.evidence[0].polarity is EvidencePolarity.SUPPORTING

    def test_an_unrecognized_priority_defaults_to_moderate(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {
            "clinical_summary": "x",
            "red_flags": [{"description": "Hypotension", "priority": "severe"}],
        }

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert result.red_flags[0].priority is RedFlagPriority.MODERATE

    def test_non_dict_items_in_the_evidence_array_are_skipped(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {"clinical_summary": "x", "evidence": ["not-an-object", {"description": "Fever"}]}

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert len(result.evidence) == 1

    def test_non_string_entries_in_recommendation_lists_are_dropped(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {
            "clinical_summary": "x",
            "suggested_investigations": ["valid", 42, None, "  "],
        }

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert result.suggested_investigations == ("valid",)

    def test_weight_out_of_range_is_clamped(self) -> None:
        parser = DefaultMedicalReasoningParser()
        payload = {
            "clinical_summary": "x",
            "evidence": [{"description": "Fever", "weight": 2.5}],
        }

        result = parser.parse(json.dumps(payload), output_format=MedicalReasoningOutputFormat.JSON)

        assert result.evidence[0].weight == 1.0


class TestParseFailures:
    def test_raises_on_malformed_json(self) -> None:
        parser = DefaultMedicalReasoningParser()
        with pytest.raises(InvalidMedicalReasoningResponseFormatError):
            parser.parse("not json at all", output_format=MedicalReasoningOutputFormat.JSON)

    def test_raises_on_empty_response(self) -> None:
        parser = DefaultMedicalReasoningParser()
        with pytest.raises(InvalidMedicalReasoningResponseFormatError):
            parser.parse("   ", output_format=MedicalReasoningOutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_list_not_an_object(self) -> None:
        parser = DefaultMedicalReasoningParser()
        with pytest.raises(InvalidMedicalReasoningResponseFormatError):
            parser.parse("[1, 2, 3]", output_format=MedicalReasoningOutputFormat.JSON)

    def test_raises_on_truncated_json(self) -> None:
        parser = DefaultMedicalReasoningParser()
        truncated = json.dumps(_VALID_PAYLOAD)[:-5]
        with pytest.raises(InvalidMedicalReasoningResponseFormatError):
            parser.parse(truncated, output_format=MedicalReasoningOutputFormat.JSON)
