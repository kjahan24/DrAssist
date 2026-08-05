"""Unit tests for `DefaultPatientEducationAnalysisParser`."""

import json

import pytest

from app.modules.patient_education_ai.domain.enums import PatientEducationOutputFormat
from app.modules.patient_education_ai.domain.exceptions import (
    InvalidPatientEducationResponseFormatError,
)
from app.modules.patient_education_ai.domain.value_objects import PatientEducationResult
from app.modules.patient_education_ai.infrastructure.parsing.patient_education_parser import (
    DefaultPatientEducationAnalysisParser,
)

_PARSER = DefaultPatientEducationAnalysisParser()


def _parse(payload: dict[str, object]) -> PatientEducationResult:
    return _PARSER.parse(json.dumps(payload), output_format=PatientEducationOutputFormat.JSON)


class TestParseHappyPath:
    def test_parses_a_full_well_formed_payload(self) -> None:
        result = _parse(
            {
                "patient_summary": "You were seen today for hypertension.",
                "diagnosis_explanation": "Hypertension means your blood pressure is high.",
                "medication_instructions": ["Take lisinopril once daily."],
                "home_care_plan": ["Check your blood pressure at home."],
                "lifestyle_advice": ["Limit alcohol intake."],
                "diet_advice": ["Follow a low-sodium diet."],
                "exercise_advice": ["Walk for 30 minutes daily."],
                "warning_signs": ["Severe headache"],
                "emergency_instructions": ["Call 911 for chest pain."],
                "follow_up_plan": ["See your doctor in 2 weeks."],
                "patient_checklist": ["Fill your prescriptions."],
                "confidence_score": 0.9,
            }
        )

        assert result.patient_summary == "You were seen today for hypertension."
        assert result.diagnosis_explanation == "Hypertension means your blood pressure is high."
        assert result.medication_instructions == ("Take lisinopril once daily.",)
        assert result.home_care_plan == ("Check your blood pressure at home.",)
        assert result.lifestyle_advice == ("Limit alcohol intake.",)
        assert result.diet_advice == ("Follow a low-sodium diet.",)
        assert result.exercise_advice == ("Walk for 30 minutes daily.",)
        assert result.warning_signs == ("Severe headache",)
        assert result.emergency_instructions == ("Call 911 for chest pain.",)
        assert result.follow_up_plan == ("See your doctor in 2 weeks.",)
        assert result.patient_checklist == ("Fill your prescriptions.",)
        assert result.confidence_score == 0.9


class TestParseMalformedJSON:
    def test_raises_when_the_raw_text_is_not_json(self) -> None:
        with pytest.raises(InvalidPatientEducationResponseFormatError):
            _PARSER.parse("not json at all", output_format=PatientEducationOutputFormat.JSON)

    def test_strips_markdown_code_fences(self) -> None:
        raw = '```json\n{"patient_summary": "ok"}\n```'
        result = _PARSER.parse(raw, output_format=PatientEducationOutputFormat.JSON)
        assert result.patient_summary == "ok"


class TestParseLenientDefaults:
    def test_missing_fields_become_empty_or_none(self) -> None:
        result = _parse({})

        assert result.patient_summary == ""
        assert result.diagnosis_explanation == ""
        assert result.medication_instructions == ()
        assert result.confidence_score is None

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

    def test_non_list_medication_instructions_become_empty_tuple(self) -> None:
        result = _parse({"medication_instructions": "not a list"})
        assert result.medication_instructions == ()

    def test_non_string_list_items_are_dropped(self) -> None:
        result = _parse({"warning_signs": ["ok", 5, None, "  "]})
        assert result.warning_signs == ("ok",)

    def test_raw_text_and_output_format_are_preserved(self) -> None:
        raw = json.dumps({"patient_summary": "ok"})
        result = _PARSER.parse(raw, output_format=PatientEducationOutputFormat.MARKDOWN)
        assert result.raw_text == raw
        assert result.output_format is PatientEducationOutputFormat.MARKDOWN
