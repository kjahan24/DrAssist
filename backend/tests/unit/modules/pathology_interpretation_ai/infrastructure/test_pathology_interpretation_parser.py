"""Unit tests for `DefaultPathologyInterpretationParser`."""

import json

import pytest

from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyFindingCategory,
    PathologyOutputFormat,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    InvalidPathologyInterpretationResponseFormatError,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationResult,
)
from app.modules.pathology_interpretation_ai.infrastructure.parsing.pathology_interpretation_parser import (  # noqa: E501
    DefaultPathologyInterpretationParser,
)

_PARSER = DefaultPathologyInterpretationParser()


def _parse(payload: dict[str, object]) -> PathologyInterpretationResult:
    return _PARSER.parse(json.dumps(payload), output_format=PathologyOutputFormat.JSON)


class TestParseHappyPath:
    def test_parses_a_full_well_formed_payload(self) -> None:
        result = _parse(
            {
                "pathology_summary": "Breast core biopsy with invasive carcinoma.",
                "key_findings": ["Invasive ductal carcinoma identified"],
                "microscopic_findings": [
                    {
                        "description": "Invasive ductal carcinoma",
                        "category": "malignant",
                        "anatomical_site": "Left breast",
                    }
                ],
                "final_impression": "Invasive ductal carcinoma, grade 2.",
                "clinical_significance": "Requires oncologic correlation and staging.",
                "correlation_recommendations": ["IHC panel: ER, PR, HER2"],
                "suggested_follow_up": ["Repeat imaging in 3 months"],
                "suggested_specialist_referral": ["Oncology"],
                "red_flag_warnings": ["Invasive carcinoma"],
                "confidence_score": 0.9,
                "clinical_reasoning": "Grounded in the described glandular architecture.",
            }
        )

        assert result.pathology_summary == "Breast core biopsy with invasive carcinoma."
        assert result.key_findings == ("Invasive ductal carcinoma identified",)
        assert result.microscopic_findings[0].description == "Invasive ductal carcinoma"
        assert result.microscopic_findings[0].category is PathologyFindingCategory.MALIGNANT
        assert result.microscopic_findings[0].anatomical_site == "Left breast"
        assert result.final_impression == "Invasive ductal carcinoma, grade 2."
        assert result.clinical_significance == "Requires oncologic correlation and staging."
        assert result.correlation_recommendations == ("IHC panel: ER, PR, HER2",)
        assert result.suggested_follow_up == ("Repeat imaging in 3 months",)
        assert result.suggested_specialist_referral == ("Oncology",)
        assert result.red_flag_warnings == ("Invasive carcinoma",)
        assert result.confidence_score == 0.9
        assert result.clinical_reasoning == ("Grounded in the described glandular architecture.")


class TestParseMalformedJSON:
    def test_raises_when_the_raw_text_is_not_json(self) -> None:
        with pytest.raises(InvalidPathologyInterpretationResponseFormatError):
            _PARSER.parse("not json at all", output_format=PathologyOutputFormat.JSON)

    def test_strips_markdown_code_fences(self) -> None:
        raw = '```json\n{"pathology_summary": "ok"}\n```'
        result = _PARSER.parse(raw, output_format=PathologyOutputFormat.JSON)
        assert result.pathology_summary == "ok"


class TestParseLenientDefaults:
    def test_missing_fields_become_empty_or_none(self) -> None:
        result = _parse({})

        assert result.pathology_summary == ""
        assert result.key_findings == ()
        assert result.microscopic_findings == ()
        assert result.final_impression == ""
        assert result.clinical_significance == ""
        assert result.confidence_score is None
        assert result.clinical_reasoning == ""

    def test_unparseable_category_defaults_to_atypical(self) -> None:
        result = _parse(
            {"microscopic_findings": [{"description": "X", "category": "not-a-real-category"}]}
        )
        assert result.microscopic_findings[0].category is PathologyFindingCategory.ATYPICAL

    def test_non_numeric_confidence_score_becomes_none(self) -> None:
        result = _parse({"confidence_score": "high"})
        assert result.confidence_score is None

    def test_confidence_score_is_not_clamped(self) -> None:
        """Deliberately not clamped — this task's own VALIDATION section
        names "invalid confidence values" as its own category, so an
        out-of-range value must survive parsing for the validator to
        reject it."""
        result = _parse({"confidence_score": 5.0})
        assert result.confidence_score == 5.0
        result = _parse({"confidence_score": -5.0})
        assert result.confidence_score == -5.0

    def test_non_list_microscopic_findings_become_empty_tuple(self) -> None:
        result = _parse({"microscopic_findings": "not a list"})
        assert result.microscopic_findings == ()

    def test_missing_anatomical_site_becomes_none(self) -> None:
        result = _parse({"microscopic_findings": [{"description": "X", "category": "benign"}]})
        assert result.microscopic_findings[0].anatomical_site is None

    def test_non_string_list_items_are_dropped(self) -> None:
        result = _parse({"correlation_recommendations": ["ok", 5, None, "  "]})
        assert result.correlation_recommendations == ("ok",)

    def test_raw_text_and_output_format_are_preserved(self) -> None:
        raw = json.dumps({"pathology_summary": "ok"})
        result = _PARSER.parse(raw, output_format=PathologyOutputFormat.MARKDOWN)
        assert result.raw_text == raw
        assert result.output_format is PathologyOutputFormat.MARKDOWN
