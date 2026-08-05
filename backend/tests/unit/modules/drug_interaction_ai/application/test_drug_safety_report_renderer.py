"""Unit tests for `DrugSafetyReportRenderer`."""

import json

from app.modules.drug_interaction_ai.application.services.drug_safety_report_renderer import (
    DrugSafetyReportRenderer,
)
from app.modules.drug_interaction_ai.domain.enums import DrugInteractionOutputFormat
from tests.unit.modules.drug_interaction_ai.application.fakes import make_issue, make_result


class TestSummarize:
    def test_includes_the_safety_summary_and_counts(self) -> None:
        result = make_result(
            interactions=(make_issue(), make_issue(description="Second issue")),
            contraindications=("Contraindicated with nitrates.",),
            warnings=("Bleeding risk.",),
        )
        service = DrugSafetyReportRenderer()

        digest = service.summarize(result)

        assert result.safety_summary in digest
        assert "2 interaction(s)" in digest
        assert "1 contraindication(s)" in digest
        assert "1 warning(s)" in digest


class TestRenderJSON:
    def test_renders_valid_json_with_all_fields(self) -> None:
        result = make_result(
            interactions=(make_issue(),), contraindications=("Do not use with nitrates.",)
        )

        rendered = DrugSafetyReportRenderer().render(result, DrugInteractionOutputFormat.JSON)

        payload = json.loads(rendered)
        assert payload["safety_summary"] == result.safety_summary
        assert payload["interactions"][0]["category"] == "drug_drug_interaction"
        assert payload["contraindications"] == ["Do not use with nitrates."]
        assert payload["confidence_score"] == result.confidence_score

    def test_includes_null_evidence_level_when_not_set(self) -> None:
        result = make_result(interactions=(make_issue(evidence_level=None),))

        rendered = DrugSafetyReportRenderer().render(result, DrugInteractionOutputFormat.JSON)

        payload = json.loads(rendered)
        assert payload["interactions"][0]["evidence_level"] is None


class TestRenderMarkdown:
    def test_includes_named_sections_that_have_content(self) -> None:
        result = make_result(
            interactions=(make_issue(),),
            contraindications=("Contraindication A",),
            warnings=("Warning A",),
            monitoring_recommendations=("Monitor INR",),
            dose_adjustment_suggestions=("Reduce dose",),
            alternative_medication_suggestions=("Consider alternative",),
            patient_counseling_points=("Take with food",),
        )

        rendered = DrugSafetyReportRenderer().render(result, DrugInteractionOutputFormat.MARKDOWN)

        assert "## Medication Safety Summary" in rendered
        assert "## Interaction List" in rendered
        assert "## Contraindications" in rendered
        assert "## Warnings" in rendered
        assert "## Monitoring Recommendations" in rendered
        assert "## Dose Adjustment Suggestions" in rendered
        assert "## Alternative Medication Suggestions" in rendered
        assert "## Patient Counseling Points" in rendered
        assert "## Confidence Score" in rendered
        assert "## Clinical Reasoning" in rendered

    def test_omits_optional_sections_when_empty(self) -> None:
        result = make_result(
            interactions=(),
            contraindications=(),
            warnings=(),
            monitoring_recommendations=(),
            dose_adjustment_suggestions=(),
            alternative_medication_suggestions=(),
            patient_counseling_points=(),
            clinical_reasoning="",
        )

        rendered = DrugSafetyReportRenderer().render(result, DrugInteractionOutputFormat.MARKDOWN)

        assert "Interaction List" not in rendered
        assert "Clinical Reasoning" not in rendered

    def test_includes_evidence_level_in_issue_line_when_present(self) -> None:
        from app.modules.drug_interaction_ai.domain.enums import EvidenceLevel

        result = make_result(interactions=(make_issue(evidence_level=EvidenceLevel.ESTABLISHED),))

        rendered = DrugSafetyReportRenderer().render(result, DrugInteractionOutputFormat.MARKDOWN)

        assert "evidence: established" in rendered


class TestRenderText:
    def test_renders_uppercased_labels(self) -> None:
        result = make_result(warnings=("Bleeding risk.",))

        rendered = DrugSafetyReportRenderer().render(result, DrugInteractionOutputFormat.TEXT)

        assert "MEDICATION SAFETY SUMMARY:" in rendered
        assert "WARNINGS:" in rendered

    def test_formats_missing_confidence_as_not_provided(self) -> None:
        result = make_result(confidence_score=None)

        rendered = DrugSafetyReportRenderer().render(result, DrugInteractionOutputFormat.TEXT)

        assert "Not provided." in rendered
