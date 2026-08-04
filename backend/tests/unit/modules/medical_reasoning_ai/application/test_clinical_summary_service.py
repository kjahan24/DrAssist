"""Unit tests for `ClinicalSummaryService`."""

import json

from app.modules.medical_reasoning_ai.application.services.clinical_summary_service import (
    ClinicalSummaryService,
)
from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    RedFlagPriority,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    MedicalReasoningResult,
    RedFlag,
)


def _result(**overrides: object) -> MedicalReasoningResult:
    defaults: dict[str, object] = {
        "clinical_summary": "Patient presents with chest pain.",
        "evidence": (
            EvidenceItem(
                description="Elevated troponin", weight=0.8, polarity=EvidencePolarity.SUPPORTING
            ),
            EvidenceItem(
                description="No ECG changes", weight=0.4, polarity=EvidencePolarity.CONTRADICTING
            ),
        ),
        "missing_information": ("No imaging provided",),
        "clinical_confidence": 0.7,
        "diagnostic_confidence": 0.6,
        "therapeutic_confidence": None,
        "risk_factors": ("Hypertension",),
        "red_flags": (RedFlag(description="Hypotension", priority=RedFlagPriority.CRITICAL),),
        "suggested_next_questions": ("Any recent travel?",),
        "suggested_investigations": ("ECG",),
        "suggested_monitoring": ("Repeat troponin in 6 hours",),
        "clinical_justification": "Grounded in the elevated troponin.",
        "raw_text": "{}",
        "output_format": MedicalReasoningOutputFormat.JSON,
    }
    defaults.update(overrides)
    return MedicalReasoningResult(**defaults)  # type: ignore[arg-type]


class TestSummarize:
    def test_includes_the_clinical_summary_and_counts(self) -> None:
        service = ClinicalSummaryService()

        digest = service.summarize(_result())

        assert "Patient presents with chest pain." in digest
        assert "1 supporting" in digest
        assert "1 contradicting" in digest
        assert "1 red flag" in digest


class TestRenderJSON:
    def test_renders_valid_json_with_all_fields(self) -> None:
        result = ClinicalSummaryService().render(_result(), MedicalReasoningOutputFormat.JSON)

        payload = json.loads(result)
        assert payload["clinical_summary"] == "Patient presents with chest pain."
        assert len(payload["evidence"]) == 2
        assert payload["evidence"][0]["polarity"] == "supporting"
        assert payload["red_flags"][0]["priority"] == "critical"
        assert payload["therapeutic_confidence"] is None


class TestRenderMarkdown:
    def test_includes_all_named_sections(self) -> None:
        result = ClinicalSummaryService().render(_result(), MedicalReasoningOutputFormat.MARKDOWN)

        assert "## Clinical Summary" in result
        assert "## Supporting Evidence" in result
        assert "## Contradicting Evidence" in result
        assert "## Missing Information" in result
        assert "## Confidence" in result
        assert "## Risk Factors" in result
        assert "## Red Flags" in result
        assert "## Suggested Next Questions" in result
        assert "## Suggested Investigations" in result
        assert "## Suggested Monitoring" in result
        assert "## Clinical Justification" in result

    def test_formats_missing_confidence_as_not_provided(self) -> None:
        result = ClinicalSummaryService().render(_result(), MedicalReasoningOutputFormat.MARKDOWN)

        assert "Not provided." in result

    def test_omits_optional_sections_when_empty(self) -> None:
        result = ClinicalSummaryService().render(
            _result(
                evidence=(),
                missing_information=(),
                risk_factors=(),
                red_flags=(),
                suggested_next_questions=(),
                suggested_investigations=(),
                suggested_monitoring=(),
            ),
            MedicalReasoningOutputFormat.MARKDOWN,
        )

        assert "Supporting Evidence" not in result
        assert "Red Flags" not in result


class TestRenderText:
    def test_renders_uppercased_labels(self) -> None:
        result = ClinicalSummaryService().render(_result(), MedicalReasoningOutputFormat.TEXT)

        assert "CLINICAL SUMMARY:" in result
        assert "SUPPORTING EVIDENCE:" in result
        assert "RED FLAGS:" in result
        assert "[CRITICAL] Hypotension" in result

    def test_includes_the_clinical_justification(self) -> None:
        result = ClinicalSummaryService().render(_result(), MedicalReasoningOutputFormat.TEXT)

        assert "CLINICAL JUSTIFICATION:\nGrounded in the elevated troponin." in result
