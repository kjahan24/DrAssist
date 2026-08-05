"""Unit tests for `PathologySummaryService`."""

import json

from app.modules.pathology_interpretation_ai.application.services.pathology_summary_service import (  # noqa: E501
    PathologySummaryService,
)
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyFindingCategory,
    PathologyOutputFormat,
)
from tests.unit.modules.pathology_interpretation_ai.application.fakes import (
    make_finding,
    make_result,
)


class TestSummarize:
    def test_includes_the_pathology_summary_and_counts(self) -> None:
        result = make_result(
            microscopic_findings=(
                make_finding(category=PathologyFindingCategory.MALIGNANT),
                make_finding(category=PathologyFindingCategory.ATYPICAL),
                make_finding(category=PathologyFindingCategory.BENIGN),
            ),
            red_flag_warnings=("Malignant finding present",),
        )
        service = PathologySummaryService()

        digest = service.summarize(result)

        assert result.pathology_summary in digest
        assert "1 malignant" in digest
        assert "1 atypical" in digest
        assert "1 benign" in digest
        assert "1 red flag" in digest


class TestRenderJSON:
    def test_renders_valid_json_with_all_fields(self) -> None:
        result = make_result(
            microscopic_findings=(make_finding(category=PathologyFindingCategory.MALIGNANT),),
            correlation_recommendations=("IHC panel recommended",),
        )

        rendered = PathologySummaryService().render(result, PathologyOutputFormat.JSON)

        payload = json.loads(rendered)
        assert payload["pathology_summary"] == result.pathology_summary
        assert payload["microscopic_findings"][0]["category"] == "malignant"
        assert payload["correlation_recommendations"] == ["IHC panel recommended"]
        assert payload["confidence_score"] == result.confidence_score


class TestRenderMarkdown:
    def test_includes_named_sections_that_have_content(self) -> None:
        result = make_result(
            microscopic_findings=(
                make_finding(description="Benign", category=PathologyFindingCategory.BENIGN),
                make_finding(description="Malignant", category=PathologyFindingCategory.MALIGNANT),
                make_finding(description="Atypical", category=PathologyFindingCategory.ATYPICAL),
            ),
            correlation_recommendations=("Correlation A",),
            suggested_follow_up=("Repeat biopsy",),
            suggested_specialist_referral=("Refer to oncology",),
            red_flag_warnings=("Urgent finding",),
        )

        rendered = PathologySummaryService().render(result, PathologyOutputFormat.MARKDOWN)

        assert "## Pathology Summary" in rendered
        assert "## Key Findings" in rendered
        assert "## Microscopic Findings" in rendered
        assert "## Benign Features" in rendered
        assert "## Malignant Features" in rendered
        assert "## Atypical Findings" in rendered
        assert "## Final Impression" in rendered
        assert "## Possible Clinical Significance" in rendered
        assert "## Correlation Recommendations" in rendered
        assert "## Suggested Follow-up" in rendered
        assert "## Suggested Specialist Referral" in rendered
        assert "## Red Flag Warnings" in rendered
        assert "## Confidence Score" in rendered
        assert "## Clinical Reasoning" in rendered

    def test_omits_optional_sections_when_empty(self) -> None:
        result = make_result(
            key_findings=(),
            microscopic_findings=(),
            final_impression="",
            clinical_significance="",
            correlation_recommendations=(),
            suggested_follow_up=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            clinical_reasoning="",
        )

        rendered = PathologySummaryService().render(result, PathologyOutputFormat.MARKDOWN)

        assert "Malignant Features" not in rendered
        assert "Red Flag Warnings" not in rendered
        assert "Clinical Reasoning" not in rendered

    def test_includes_anatomical_site_when_present(self) -> None:
        result = make_result(
            microscopic_findings=(
                make_finding(
                    description="Carcinoma",
                    category=PathologyFindingCategory.MALIGNANT,
                    anatomical_site="Left breast",
                ),
            )
        )

        rendered = PathologySummaryService().render(result, PathologyOutputFormat.MARKDOWN)

        assert "Carcinoma (Left breast)" in rendered


class TestRenderText:
    def test_renders_uppercased_labels(self) -> None:
        result = make_result(red_flag_warnings=("Malignant finding",))

        rendered = PathologySummaryService().render(result, PathologyOutputFormat.TEXT)

        assert "PATHOLOGY SUMMARY:" in rendered
        assert "RED FLAG WARNINGS:" in rendered

    def test_formats_missing_confidence_as_not_provided(self) -> None:
        result = make_result(confidence_score=None)

        rendered = PathologySummaryService().render(result, PathologyOutputFormat.TEXT)

        assert "Not provided." in rendered
