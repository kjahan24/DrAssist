"""Unit tests for `DefaultLabInterpretationParser`."""

import json

import pytest

from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
)
from app.modules.lab_interpretation_ai.domain.exceptions import (
    InvalidLabInterpretationResponseFormatError,
)
from app.modules.lab_interpretation_ai.domain.value_objects import LabInterpretationResult
from app.modules.lab_interpretation_ai.infrastructure.parsing.lab_interpretation_parser import (
    DefaultLabInterpretationParser,
)

_PARSER = DefaultLabInterpretationParser()


def _parse(payload: dict[str, object]) -> LabInterpretationResult:
    return _PARSER.parse(json.dumps(payload), output_format=LabInterpretationOutputFormat.JSON)


class TestParseHappyPath:
    def test_parses_a_full_well_formed_payload(self) -> None:
        result = _parse(
            {
                "overall_interpretation": "Electrolytes reviewed.",
                "findings": [
                    {
                        "test_name": "Potassium",
                        "value": "6.8",
                        "numeric_value": 6.8,
                        "unit": "mmol/L",
                        "flag": "critical_high",
                    }
                ],
                "clinical_significance": "Hyperkalemia noted.",
                "supporting_evidence": ["Potassium markedly elevated"],
                "potential_causes": ["Renal failure"],
                "suggested_follow_up_tests": ["Repeat BMP"],
                "monitoring_recommendations": ["Cardiac monitoring"],
                "red_flag_warnings": ["Critical potassium"],
                "confidence_score": 0.85,
            }
        )

        assert result.overall_interpretation == "Electrolytes reviewed."
        assert result.findings[0].test_name == "Potassium"
        assert result.findings[0].flag is LabFindingFlag.CRITICAL_HIGH
        assert result.clinical_significance == "Hyperkalemia noted."
        assert result.supporting_evidence == ("Potassium markedly elevated",)
        assert result.potential_causes == ("Renal failure",)
        assert result.suggested_follow_up_tests == ("Repeat BMP",)
        assert result.monitoring_recommendations == ("Cardiac monitoring",)
        assert result.red_flag_warnings == ("Critical potassium",)
        assert result.confidence_score == 0.85


class TestParseMalformedJSON:
    def test_raises_when_the_raw_text_is_not_json(self) -> None:
        with pytest.raises(InvalidLabInterpretationResponseFormatError):
            _PARSER.parse("not json at all", output_format=LabInterpretationOutputFormat.JSON)

    def test_strips_markdown_code_fences(self) -> None:
        raw = '```json\n{"overall_interpretation": "ok"}\n```'
        result = _PARSER.parse(raw, output_format=LabInterpretationOutputFormat.JSON)
        assert result.overall_interpretation == "ok"


class TestParseLenientDefaults:
    def test_missing_fields_become_empty_or_none(self) -> None:
        result = _parse({})

        assert result.overall_interpretation == ""
        assert result.findings == ()
        assert result.clinical_significance == ""
        assert result.supporting_evidence == ()
        assert result.confidence_score is None

    def test_unparseable_flag_defaults_to_normal(self) -> None:
        result = _parse({"findings": [{"test_name": "X", "value": "1", "flag": "not-a-real-flag"}]})
        assert result.findings[0].flag is LabFindingFlag.NORMAL

    def test_non_numeric_confidence_score_becomes_none(self) -> None:
        result = _parse({"confidence_score": "high"})
        assert result.confidence_score is None

    def test_confidence_score_is_clamped_to_zero_one(self) -> None:
        result = _parse({"confidence_score": 5.0})
        assert result.confidence_score == 1.0
        result = _parse({"confidence_score": -5.0})
        assert result.confidence_score == 0.0

    def test_non_list_findings_become_empty_tuple(self) -> None:
        result = _parse({"findings": "not a list"})
        assert result.findings == ()

    def test_missing_numeric_value_and_unit_in_a_finding_become_none(self) -> None:
        result = _parse({"findings": [{"test_name": "X", "value": "trace"}]})
        assert result.findings[0].numeric_value is None
        assert result.findings[0].unit is None

    def test_non_string_list_items_are_dropped(self) -> None:
        result = _parse({"supporting_evidence": ["ok", 5, None, "  "]})
        assert result.supporting_evidence == ("ok",)

    def test_raw_text_and_output_format_are_preserved(self) -> None:
        raw = json.dumps({"overall_interpretation": "ok"})
        result = _PARSER.parse(raw, output_format=LabInterpretationOutputFormat.MARKDOWN)
        assert result.raw_text == raw
        assert result.output_format is LabInterpretationOutputFormat.MARKDOWN
