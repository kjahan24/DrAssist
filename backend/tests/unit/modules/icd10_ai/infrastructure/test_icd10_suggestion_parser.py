"""Unit tests for `DefaultICD10SuggestionParser`."""

import json

import pytest

from app.modules.icd10_ai.domain.enums import DiagnosisFlag, ICD10OutputFormat
from app.modules.icd10_ai.domain.exceptions import InvalidICD10ResponseFormatError
from app.modules.icd10_ai.infrastructure.parsing.icd10_suggestion_parser import (
    DefaultICD10SuggestionParser,
)

_VALID_PAYLOAD = {
    "suggestions": [
        {
            "icd10_code": "J06.9",
            "diagnosis_name": "Acute upper respiratory infection, unspecified",
            "confidence_score": 0.9,
            "clinical_reasoning": "Supported by sore throat and fever",
            "supporting_evidence": "sore throat, fever",
            "flag": "primary",
        },
        {
            "icd10_code": "R50.9",
            "diagnosis_name": "Fever, unspecified",
            "confidence_score": 0.4,
            "clinical_reasoning": "Elevated temperature",
            "supporting_evidence": "temperature 38.5C",
            "flag": "secondary",
        },
    ]
}


class TestParsePlainJSON:
    def test_parses_all_suggestions(self) -> None:
        parser = DefaultICD10SuggestionParser()

        suggestion_set = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=ICD10OutputFormat.JSON
        )

        assert len(suggestion_set.suggestions) == 2
        assert suggestion_set.suggestions[0].icd10_code == "J06.9"
        assert suggestion_set.suggestions[0].confidence_score == 0.9
        assert suggestion_set.suggestions[0].flag is DiagnosisFlag.PRIMARY
        assert suggestion_set.suggestions[1].flag is DiagnosisFlag.SECONDARY

    def test_carries_through_the_requested_output_format(self) -> None:
        parser = DefaultICD10SuggestionParser()

        suggestion_set = parser.parse(
            json.dumps(_VALID_PAYLOAD), output_format=ICD10OutputFormat.MARKDOWN
        )

        assert suggestion_set.output_format is ICD10OutputFormat.MARKDOWN

    def test_preserves_the_original_raw_text(self) -> None:
        parser = DefaultICD10SuggestionParser()
        raw_text = json.dumps(_VALID_PAYLOAD)

        suggestion_set = parser.parse(raw_text, output_format=ICD10OutputFormat.JSON)

        assert suggestion_set.raw_text == raw_text

    def test_empty_suggestions_array_parses_to_an_empty_set(self) -> None:
        parser = DefaultICD10SuggestionParser()

        suggestion_set = parser.parse(
            json.dumps({"suggestions": []}), output_format=ICD10OutputFormat.JSON
        )

        assert suggestion_set.suggestions == ()


class TestParseFencedJSON:
    def test_parses_json_wrapped_in_a_labeled_fence(self) -> None:
        parser = DefaultICD10SuggestionParser()
        raw = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"

        suggestion_set = parser.parse(raw, output_format=ICD10OutputFormat.JSON)

        assert suggestion_set.suggestions[0].icd10_code == "J06.9"

    def test_parses_json_wrapped_in_an_unlabeled_fence(self) -> None:
        parser = DefaultICD10SuggestionParser()
        raw = f"```\n{json.dumps(_VALID_PAYLOAD)}\n```"

        suggestion_set = parser.parse(raw, output_format=ICD10OutputFormat.JSON)

        assert suggestion_set.suggestions[1].icd10_code == "R50.9"


class TestParseMissingFields:
    def test_missing_fields_in_a_suggestion_become_empty_or_none(self) -> None:
        parser = DefaultICD10SuggestionParser()
        payload = {"suggestions": [{"icd10_code": "J06.9"}]}

        suggestion_set = parser.parse(json.dumps(payload), output_format=ICD10OutputFormat.JSON)

        suggestion = suggestion_set.suggestions[0]
        assert suggestion.icd10_code == "J06.9"
        assert suggestion.diagnosis_name == ""
        assert suggestion.confidence_score is None
        assert suggestion.clinical_reasoning == ""
        assert suggestion.supporting_evidence == ""
        assert suggestion.flag is DiagnosisFlag.SECONDARY

    def test_a_boolean_confidence_score_is_not_treated_as_a_number(self) -> None:
        parser = DefaultICD10SuggestionParser()
        payload = {"suggestions": [{"icd10_code": "J06.9", "confidence_score": True}]}

        suggestion_set = parser.parse(json.dumps(payload), output_format=ICD10OutputFormat.JSON)

        assert suggestion_set.suggestions[0].confidence_score is None

    def test_an_unrecognized_flag_value_defaults_to_secondary(self) -> None:
        parser = DefaultICD10SuggestionParser()
        payload = {"suggestions": [{"icd10_code": "J06.9", "flag": "not-a-flag"}]}

        suggestion_set = parser.parse(json.dumps(payload), output_format=ICD10OutputFormat.JSON)

        assert suggestion_set.suggestions[0].flag is DiagnosisFlag.SECONDARY

    def test_non_dict_items_in_the_suggestions_array_are_skipped(self) -> None:
        parser = DefaultICD10SuggestionParser()
        payload = {"suggestions": ["not-an-object", {"icd10_code": "J06.9"}]}

        suggestion_set = parser.parse(json.dumps(payload), output_format=ICD10OutputFormat.JSON)

        assert len(suggestion_set.suggestions) == 1
        assert suggestion_set.suggestions[0].icd10_code == "J06.9"


class TestParseFailures:
    def test_raises_on_malformed_json(self) -> None:
        parser = DefaultICD10SuggestionParser()
        with pytest.raises(InvalidICD10ResponseFormatError):
            parser.parse("not json at all", output_format=ICD10OutputFormat.JSON)

    def test_raises_on_empty_response(self) -> None:
        parser = DefaultICD10SuggestionParser()
        with pytest.raises(InvalidICD10ResponseFormatError):
            parser.parse("   ", output_format=ICD10OutputFormat.JSON)

    def test_raises_when_top_level_json_is_a_list_not_an_object(self) -> None:
        parser = DefaultICD10SuggestionParser()
        with pytest.raises(InvalidICD10ResponseFormatError):
            parser.parse("[1, 2, 3]", output_format=ICD10OutputFormat.JSON)

    def test_raises_when_suggestions_key_is_missing(self) -> None:
        parser = DefaultICD10SuggestionParser()
        with pytest.raises(InvalidICD10ResponseFormatError):
            parser.parse(json.dumps({"not_suggestions": []}), output_format=ICD10OutputFormat.JSON)

    def test_raises_when_suggestions_is_not_a_list(self) -> None:
        parser = DefaultICD10SuggestionParser()
        with pytest.raises(InvalidICD10ResponseFormatError):
            parser.parse(
                json.dumps({"suggestions": "not-a-list"}), output_format=ICD10OutputFormat.JSON
            )

    def test_raises_on_truncated_json(self) -> None:
        parser = DefaultICD10SuggestionParser()
        truncated = json.dumps(_VALID_PAYLOAD)[:-5]
        with pytest.raises(InvalidICD10ResponseFormatError):
            parser.parse(truncated, output_format=ICD10OutputFormat.JSON)
