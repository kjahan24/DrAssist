"""Unit tests for `DefaultRadiologyInterpretationParser`."""

import json

import pytest

from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyFindingCategory,
    RadiologyOutputFormat,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    InvalidRadiologyInterpretationResponseFormatError,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationResult,
)
from app.modules.radiology_interpretation_ai.infrastructure.parsing.radiology_interpretation_parser import (  # noqa: E501
    DefaultRadiologyInterpretationParser,
)

_PARSER = DefaultRadiologyInterpretationParser()


def _parse(payload: dict[str, object]) -> RadiologyInterpretationResult:
    return _PARSER.parse(json.dumps(payload), output_format=RadiologyOutputFormat.JSON)


class TestParseHappyPath:
    def test_parses_a_full_well_formed_payload(self) -> None:
        result = _parse(
            {
                "examination_summary": "Chest X-ray with large pneumothorax.",
                "findings": [
                    {
                        "description": "Large right pneumothorax",
                        "category": "critical",
                        "anatomical_region": "Right hemithorax",
                    }
                ],
                "clinical_significance": "Requires urgent decompression.",
                "differential_imaging_considerations": ["Tension pneumothorax"],
                "suggested_follow_up_imaging": ["Repeat chest X-ray after chest tube"],
                "suggested_specialist_referral": ["Thoracic surgery"],
                "red_flag_warnings": ["Large pneumothorax"],
                "confidence_score": 0.9,
                "clinical_reasoning": "Grounded in the described pleural line and lucency.",
            }
        )

        assert result.examination_summary == "Chest X-ray with large pneumothorax."
        assert result.findings[0].description == "Large right pneumothorax"
        assert result.findings[0].category is RadiologyFindingCategory.CRITICAL
        assert result.findings[0].anatomical_region == "Right hemithorax"
        assert result.clinical_significance == "Requires urgent decompression."
        assert result.differential_imaging_considerations == ("Tension pneumothorax",)
        assert result.suggested_follow_up_imaging == ("Repeat chest X-ray after chest tube",)
        assert result.suggested_specialist_referral == ("Thoracic surgery",)
        assert result.red_flag_warnings == ("Large pneumothorax",)
        assert result.confidence_score == 0.9
        assert result.clinical_reasoning == ("Grounded in the described pleural line and lucency.")


class TestParseMalformedJSON:
    def test_raises_when_the_raw_text_is_not_json(self) -> None:
        with pytest.raises(InvalidRadiologyInterpretationResponseFormatError):
            _PARSER.parse("not json at all", output_format=RadiologyOutputFormat.JSON)

    def test_strips_markdown_code_fences(self) -> None:
        raw = '```json\n{"examination_summary": "ok"}\n```'
        result = _PARSER.parse(raw, output_format=RadiologyOutputFormat.JSON)
        assert result.examination_summary == "ok"


class TestParseLenientDefaults:
    def test_missing_fields_become_empty_or_none(self) -> None:
        result = _parse({})

        assert result.examination_summary == ""
        assert result.findings == ()
        assert result.clinical_significance == ""
        assert result.differential_imaging_considerations == ()
        assert result.confidence_score is None
        assert result.clinical_reasoning == ""

    def test_unparseable_category_defaults_to_abnormal(self) -> None:
        result = _parse({"findings": [{"description": "X", "category": "not-a-real-category"}]})
        assert result.findings[0].category is RadiologyFindingCategory.ABNORMAL

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

    def test_non_list_findings_become_empty_tuple(self) -> None:
        result = _parse({"findings": "not a list"})
        assert result.findings == ()

    def test_missing_anatomical_region_becomes_none(self) -> None:
        result = _parse({"findings": [{"description": "X", "category": "normal"}]})
        assert result.findings[0].anatomical_region is None

    def test_non_string_list_items_are_dropped(self) -> None:
        result = _parse({"differential_imaging_considerations": ["ok", 5, None, "  "]})
        assert result.differential_imaging_considerations == ("ok",)

    def test_raw_text_and_output_format_are_preserved(self) -> None:
        raw = json.dumps({"examination_summary": "ok"})
        result = _PARSER.parse(raw, output_format=RadiologyOutputFormat.MARKDOWN)
        assert result.raw_text == raw
        assert result.output_format is RadiologyOutputFormat.MARKDOWN
