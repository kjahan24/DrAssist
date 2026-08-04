"""Unit tests for `ICD10SuggestionRenderer`."""

import json

from app.modules.icd10_ai.application.services.icd10_suggestion_renderer import (
    ICD10SuggestionRenderer,
)
from app.modules.icd10_ai.domain.enums import DiagnosisFlag, ICD10OutputFormat
from app.modules.icd10_ai.domain.value_objects import ICD10Suggestion, ICD10SuggestionSet


def _suggestion_set() -> ICD10SuggestionSet:
    return ICD10SuggestionSet(
        suggestions=(
            ICD10Suggestion(
                icd10_code="J06.9",
                diagnosis_name="Acute upper respiratory infection, unspecified",
                confidence_score=0.9,
                clinical_reasoning="Supported by sore throat and fever",
                supporting_evidence="sore throat, fever",
                flag=DiagnosisFlag.PRIMARY,
            ),
            ICD10Suggestion(
                icd10_code="R50.9",
                diagnosis_name="Fever, unspecified",
                confidence_score=None,
                clinical_reasoning="Elevated temperature noted",
                supporting_evidence="temperature 38.5C",
                flag=DiagnosisFlag.SECONDARY,
            ),
        ),
        raw_text="{}",
        output_format=ICD10OutputFormat.JSON,
    )


class TestICD10SuggestionRendererJSON:
    def test_renders_valid_json_with_all_suggestions(self) -> None:
        result = ICD10SuggestionRenderer().render(_suggestion_set(), ICD10OutputFormat.JSON)

        payload = json.loads(result)
        assert len(payload["suggestions"]) == 2
        assert payload["suggestions"][0]["icd10_code"] == "J06.9"
        assert payload["suggestions"][0]["confidence_score"] == 0.9
        assert payload["suggestions"][0]["flag"] == "primary"

    def test_null_confidence_score_round_trips_as_json_null(self) -> None:
        result = ICD10SuggestionRenderer().render(_suggestion_set(), ICD10OutputFormat.JSON)

        payload = json.loads(result)
        assert payload["suggestions"][1]["confidence_score"] is None


class TestICD10SuggestionRendererMarkdown:
    def test_renders_a_heading_per_suggestion(self) -> None:
        result = ICD10SuggestionRenderer().render(_suggestion_set(), ICD10OutputFormat.MARKDOWN)

        assert "## J06.9" in result
        assert "## R50.9" in result
        assert "(primary)" in result
        assert "(secondary)" in result

    def test_formats_missing_confidence_as_not_provided(self) -> None:
        result = ICD10SuggestionRenderer().render(_suggestion_set(), ICD10OutputFormat.MARKDOWN)

        assert "Not provided." in result

    def test_formats_present_confidence_to_two_decimal_places(self) -> None:
        result = ICD10SuggestionRenderer().render(_suggestion_set(), ICD10OutputFormat.MARKDOWN)

        assert "0.90" in result


class TestICD10SuggestionRendererText:
    def test_renders_uppercased_flag_and_labels(self) -> None:
        result = ICD10SuggestionRenderer().render(_suggestion_set(), ICD10OutputFormat.TEXT)

        assert "[PRIMARY]" in result
        assert "[SECONDARY]" in result
        assert "CLINICAL REASONING:" in result
        assert "SUPPORTING EVIDENCE:" in result

    def test_includes_the_diagnosis_name(self) -> None:
        result = ICD10SuggestionRenderer().render(_suggestion_set(), ICD10OutputFormat.TEXT)

        assert "Acute upper respiratory infection, unspecified" in result


class TestICD10SuggestionRendererEmptySet:
    def test_json_renders_an_empty_suggestions_array(self) -> None:
        empty = ICD10SuggestionSet(
            suggestions=(), raw_text="{}", output_format=ICD10OutputFormat.JSON
        )

        result = ICD10SuggestionRenderer().render(empty, ICD10OutputFormat.JSON)

        assert json.loads(result) == {"suggestions": []}

    def test_markdown_renders_an_empty_string(self) -> None:
        empty = ICD10SuggestionSet(
            suggestions=(), raw_text="{}", output_format=ICD10OutputFormat.JSON
        )

        result = ICD10SuggestionRenderer().render(empty, ICD10OutputFormat.MARKDOWN)

        assert result == ""
