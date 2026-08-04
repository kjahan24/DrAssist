"""Unit tests for `DifferentialDiagnosisRenderer`."""

import json

from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_renderer import (  # noqa: E501
    DifferentialDiagnosisRenderer,
)
from app.modules.differential_diagnosis_ai.domain.enums import (
    DifferentialOutputFormat,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisResult,
)


def _result(**overrides: object) -> DifferentialDiagnosisResult:
    defaults: dict[str, object] = {
        "candidates": (
            DifferentialDiagnosisCandidate(
                disease_name="Pneumonia",
                icd10_code="J18.9",
                confidence_score=0.9,
                clinical_reasoning="Consistent with fever and productive cough",
                supporting_findings=("fever", "productive cough"),
                findings_against=("no consolidation on exam",),
                recommended_next_tests=("chest x-ray",),
                red_flag_indicators=(),
                urgency_level=UrgencyLevel.URGENT,
            ),
            DifferentialDiagnosisCandidate(
                disease_name="Bronchitis",
                icd10_code=None,
                confidence_score=None,
                clinical_reasoning="Also plausible",
                supporting_findings=(),
                findings_against=(),
                recommended_next_tests=(),
                red_flag_indicators=(),
                urgency_level=UrgencyLevel.ROUTINE,
            ),
        ),
        "serious_diagnoses_not_to_miss": ("Pulmonary Embolism",),
        "suggested_investigations": ("CBC",),
        "suggested_referrals": ("Pulmonology",),
        "raw_text": "{}",
        "output_format": DifferentialOutputFormat.JSON,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisResult(**defaults)  # type: ignore[arg-type]


class TestDifferentialDiagnosisRendererJSON:
    def test_renders_valid_json_with_candidates_and_lists(self) -> None:
        result = DifferentialDiagnosisRenderer().render(_result(), DifferentialOutputFormat.JSON)

        payload = json.loads(result)
        assert payload["most_likely_diagnosis"] == "Pneumonia"
        assert len(payload["candidates"]) == 2
        assert payload["candidates"][0]["disease_name"] == "Pneumonia"
        assert payload["candidates"][0]["urgency_level"] == "urgent"
        assert payload["serious_diagnoses_not_to_miss"] == ["Pulmonary Embolism"]

    def test_null_confidence_score_round_trips_as_json_null(self) -> None:
        result = DifferentialDiagnosisRenderer().render(_result(), DifferentialOutputFormat.JSON)

        payload = json.loads(result)
        assert payload["candidates"][1]["confidence_score"] is None


class TestDifferentialDiagnosisRendererMarkdown:
    def test_includes_most_likely_diagnosis_heading(self) -> None:
        result = DifferentialDiagnosisRenderer().render(
            _result(), DifferentialOutputFormat.MARKDOWN
        )

        assert "## Most Likely Diagnosis" in result
        assert "Pneumonia" in result

    def test_renders_a_heading_per_candidate(self) -> None:
        result = DifferentialDiagnosisRenderer().render(
            _result(), DifferentialOutputFormat.MARKDOWN
        )

        assert "## Pneumonia (J18.9)" in result
        assert "## Bronchitis" in result

    def test_includes_serious_diagnoses_and_recommendation_sections(self) -> None:
        result = DifferentialDiagnosisRenderer().render(
            _result(), DifferentialOutputFormat.MARKDOWN
        )

        assert "## Serious Diagnoses Not To Miss" in result
        assert "## Suggested Investigations" in result
        assert "## Suggested Referrals" in result

    def test_omits_optional_sections_when_empty(self) -> None:
        result = DifferentialDiagnosisRenderer().render(
            _result(
                serious_diagnoses_not_to_miss=(),
                suggested_investigations=(),
                suggested_referrals=(),
            ),
            DifferentialOutputFormat.MARKDOWN,
        )

        assert "Serious Diagnoses Not To Miss" not in result


class TestDifferentialDiagnosisRendererText:
    def test_renders_uppercased_disease_name_and_urgency(self) -> None:
        result = DifferentialDiagnosisRenderer().render(_result(), DifferentialOutputFormat.TEXT)

        assert "PNEUMONIA (J18.9) [URGENT]" in result
        assert "SUPPORTING FINDINGS:" in result
        assert "FINDINGS AGAINST:" in result

    def test_includes_most_likely_diagnosis_line(self) -> None:
        result = DifferentialDiagnosisRenderer().render(_result(), DifferentialOutputFormat.TEXT)

        assert "MOST LIKELY DIAGNOSIS: Pneumonia" in result

    def test_formats_missing_findings_as_none_noted(self) -> None:
        result = DifferentialDiagnosisRenderer().render(_result(), DifferentialOutputFormat.TEXT)

        assert "None noted." in result
