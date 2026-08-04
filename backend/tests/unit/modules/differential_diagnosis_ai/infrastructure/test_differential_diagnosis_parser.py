"""Unit tests for `DefaultDifferentialDiagnosisParser`."""

import json

import pytest

from app.modules.differential_diagnosis_ai.domain.enums import (
    DifferentialOutputFormat,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.exceptions import (
    InvalidDifferentialResponseFormatError,
)
from app.modules.differential_diagnosis_ai.infrastructure.parsing.differential_diagnosis_parser import (  # noqa: E501
    DefaultDifferentialDiagnosisParser,
)

_VALID_PAYLOAD = {
    "candidates": [
        {
            "disease_name": "Pneumonia",
            "icd10_code": "J18.9",
            "confidence_score": 0.9,
            "clinical_reasoning": "Consistent with fever and productive cough",
            "supporting_findings": ["fever", "productive cough"],
            "findings_against": ["no consolidation on exam"],
            "recommended_next_tests": ["chest x-ray"],
            "red_flag_indicators": [],
            "urgency_level": "urgent",
        },
        {
            "disease_name": "Bronchitis",
            "icd10_code": None,
            "confidence_score": 0.4,
            "clinical_reasoning": "Also plausible",
            "supporting_findings": [],
            "findings_against": [],
            "recommended_next_tests": [],
            "red_flag_indicators": [],
            "urgency_level": "routine",
        },
    ],
    "serious_diagnoses_not_to_miss": ["Pulmonary Embolism"],
    "suggested_investigations": ["CBC"],
    "suggested_referrals": ["Pulmonology"],
}


class TestParsePlainJSON:
    def test_parses_all_candidate_fields(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=DifferentialOutputFormat.JSON
        )

        candidate = result.candidates[0]
        assert candidate.disease_name == "Pneumonia"
        assert candidate.icd10_code == "J18.9"
        assert candidate.confidence_score == 0.9
        assert candidate.urgency_level is UrgencyLevel.URGENT

    def test_parses_a_null_icd10_code(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=DifferentialOutputFormat.JSON
        )

        assert result.candidates[1].icd10_code is None

    def test_parses_top_level_lists(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=DifferentialOutputFormat.JSON
        )

        assert result.serious_diagnoses_not_to_miss == ("Pulmonary Embolism",)
        assert result.suggested_investigations == ("CBC",)
        assert result.suggested_referrals == ("Pulmonology",)

    def test_carries_through_the_requested_output_format(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()

        result = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=DifferentialOutputFormat.MARKDOWN
        )

        assert result.output_format is DifferentialOutputFormat.MARKDOWN

    def test_preserves_the_original_raw_text(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        raw_text = json.dumps(_VALID_PAYLOAD)

        result = parser.parse(raw_text, output_format=DifferentialOutputFormat.JSON)

        assert result.raw_text == raw_text

    def test_empty_candidates_array_parses_to_an_empty_result(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()

        result = parser.parse(
            json.dumps({"candidates": []}), output_format=DifferentialOutputFormat.JSON
        )

        assert result.candidates == ()

    def test_missing_optional_top_level_keys_default_to_empty(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()

        result = parser.parse(
            json.dumps({"candidates": []}), output_format=DifferentialOutputFormat.JSON
        )

        assert result.serious_diagnoses_not_to_miss == ()
        assert result.suggested_investigations == ()
        assert result.suggested_referrals == ()


class TestParseFencedJSON:
    def test_parses_json_wrapped_in_a_labeled_fence(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        raw = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"

        result = parser.parse(raw, output_format=DifferentialOutputFormat.JSON)

        assert result.candidates[0].disease_name == "Pneumonia"

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        raw = f"```\n{json.dumps(_VALID_PAYLOAD)}\n```"

        result = parser.parse(raw, output_format=DifferentialOutputFormat.JSON)

        assert result.candidates[1].disease_name == "Bronchitis"


class TestParseMissingOrMalformedFields:
    def test_missing_fields_in_a_candidate_become_empty_or_none(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        payload = {"candidates": [{"disease_name": "Pneumonia"}]}

        result = parser.parse(json.dumps(payload), output_format=DifferentialOutputFormat.JSON)

        candidate = result.candidates[0]
        assert candidate.disease_name == "Pneumonia"
        assert candidate.icd10_code is None
        assert candidate.confidence_score is None
        assert candidate.clinical_reasoning == ""
        assert candidate.supporting_findings == ()
        assert candidate.urgency_level is UrgencyLevel.ROUTINE

    def test_a_boolean_confidence_score_is_not_treated_as_a_number(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        payload = {"candidates": [{"disease_name": "Pneumonia", "confidence_score": True}]}

        result = parser.parse(json.dumps(payload), output_format=DifferentialOutputFormat.JSON)

        assert result.candidates[0].confidence_score is None

    def test_an_unrecognized_urgency_level_defaults_to_routine(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        payload = {"candidates": [{"disease_name": "Pneumonia", "urgency_level": "critical"}]}

        result = parser.parse(json.dumps(payload), output_format=DifferentialOutputFormat.JSON)

        assert result.candidates[0].urgency_level is UrgencyLevel.ROUTINE

    def test_non_dict_items_in_the_candidates_array_are_skipped(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        payload = {"candidates": ["not-an-object", {"disease_name": "Pneumonia"}]}

        result = parser.parse(json.dumps(payload), output_format=DifferentialOutputFormat.JSON)

        assert len(result.candidates) == 1

    def test_non_string_entries_in_recommendation_lists_are_dropped(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        payload = {"candidates": [], "suggested_investigations": ["valid", 42, None, "  "]}

        result = parser.parse(json.dumps(payload), output_format=DifferentialOutputFormat.JSON)

        assert result.suggested_investigations == ("valid",)


class TestParseFailures:
    def test_raises_on_malformed_json(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        with pytest.raises(InvalidDifferentialResponseFormatError):
            parser.parse("not json at all", output_format=DifferentialOutputFormat.JSON)

    def test_raises_on_empty_response(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        with pytest.raises(InvalidDifferentialResponseFormatError):
            parser.parse("   ", output_format=DifferentialOutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_list_not_an_object(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        with pytest.raises(InvalidDifferentialResponseFormatError):
            parser.parse("[1, 2, 3]", output_format=DifferentialOutputFormat.JSON)

    def test_raises_when_candidates_key_is_missing(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        with pytest.raises(InvalidDifferentialResponseFormatError):
            parser.parse(
                json.dumps({"not_candidates": []}), output_format=DifferentialOutputFormat.JSON
            )

    def test_raises_when_candidates_is_not_a_list(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        with pytest.raises(InvalidDifferentialResponseFormatError):
            parser.parse(
                json.dumps({"candidates": "not-a-list"}),
                output_format=DifferentialOutputFormat.JSON,
            )

    def test_raises_on_truncated_json(self) -> None:
        parser = DefaultDifferentialDiagnosisParser()
        truncated = json.dumps(_VALID_PAYLOAD)[:-5]
        with pytest.raises(InvalidDifferentialResponseFormatError):
            parser.parse(truncated, output_format=DifferentialOutputFormat.JSON)
