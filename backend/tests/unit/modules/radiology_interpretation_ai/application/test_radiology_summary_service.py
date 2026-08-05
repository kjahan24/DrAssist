"""Unit tests for `RadiologySummaryService`."""

import json

from app.modules.radiology_interpretation_ai.application.services.radiology_summary_service import (  # noqa: E501
    RadiologySummaryService,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyFindingCategory,
    RadiologyOutputFormat,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    make_finding,
    make_result,
)


class TestSummarize:
    def test_includes_the_examination_summary_and_counts(self) -> None:
        result = make_result(
            findings=(
                make_finding(category=RadiologyFindingCategory.ABNORMAL),
                make_finding(category=RadiologyFindingCategory.CRITICAL),
                make_finding(category=RadiologyFindingCategory.INCIDENTAL),
            ),
            red_flag_warnings=("Critical finding present",),
        )
        service = RadiologySummaryService()

        digest = service.summarize(result)

        assert result.examination_summary in digest
        assert "1 abnormal" in digest
        assert "1 critical" in digest
        assert "1 incidental" in digest
        assert "1 red flag" in digest


class TestRenderJSON:
    def test_renders_valid_json_with_all_fields(self) -> None:
        result = make_result(
            findings=(make_finding(category=RadiologyFindingCategory.CRITICAL),),
            differential_imaging_considerations=("Possible malignancy",),
        )

        rendered = RadiologySummaryService().render(result, RadiologyOutputFormat.JSON)

        payload = json.loads(rendered)
        assert payload["examination_summary"] == result.examination_summary
        assert payload["findings"][0]["category"] == "critical"
        assert payload["differential_imaging_considerations"] == ["Possible malignancy"]
        assert payload["confidence_score"] == result.confidence_score


class TestRenderMarkdown:
    def test_includes_named_sections_that_have_content(self) -> None:
        result = make_result(
            findings=(
                make_finding(description="Normal", category=RadiologyFindingCategory.NORMAL),
                make_finding(description="Abnormal", category=RadiologyFindingCategory.ABNORMAL),
                make_finding(
                    description="Incidental", category=RadiologyFindingCategory.INCIDENTAL
                ),
                make_finding(description="Critical", category=RadiologyFindingCategory.CRITICAL),
            ),
            differential_imaging_considerations=("Consideration A",),
            suggested_follow_up_imaging=("Repeat CT",),
            suggested_specialist_referral=("Refer to pulmonology",),
            red_flag_warnings=("Urgent finding",),
        )

        rendered = RadiologySummaryService().render(result, RadiologyOutputFormat.MARKDOWN)

        assert "## Examination Summary" in rendered
        assert "## Important Findings" in rendered
        assert "## Normal Findings" in rendered
        assert "## Abnormal Findings" in rendered
        assert "## Incidental Findings" in rendered
        assert "## Critical Findings" in rendered
        assert "## Possible Clinical Significance" in rendered
        assert "## Differential Imaging Considerations" in rendered
        assert "## Suggested Follow-up Imaging" in rendered
        assert "## Suggested Specialist Referral" in rendered
        assert "## Red Flag Warnings" in rendered
        assert "## Confidence Score" in rendered
        assert "## Clinical Reasoning" in rendered

    def test_omits_optional_sections_when_empty(self) -> None:
        result = make_result(
            findings=(),
            clinical_significance="",
            differential_imaging_considerations=(),
            suggested_follow_up_imaging=(),
            suggested_specialist_referral=(),
            red_flag_warnings=(),
            clinical_reasoning="",
        )

        rendered = RadiologySummaryService().render(result, RadiologyOutputFormat.MARKDOWN)

        assert "Critical Findings" not in rendered
        assert "Red Flag Warnings" not in rendered
        assert "Clinical Reasoning" not in rendered

    def test_includes_anatomical_region_when_present(self) -> None:
        result = make_result(
            findings=(
                make_finding(
                    description="Opacity",
                    category=RadiologyFindingCategory.ABNORMAL,
                    anatomical_region="Right lower lobe",
                ),
            )
        )

        rendered = RadiologySummaryService().render(result, RadiologyOutputFormat.MARKDOWN)

        assert "Opacity (Right lower lobe)" in rendered


class TestRenderText:
    def test_renders_uppercased_labels(self) -> None:
        result = make_result(red_flag_warnings=("Critical finding",))

        rendered = RadiologySummaryService().render(result, RadiologyOutputFormat.TEXT)

        assert "EXAMINATION SUMMARY:" in rendered
        assert "RED FLAG WARNINGS:" in rendered

    def test_formats_missing_confidence_as_not_provided(self) -> None:
        result = make_result(confidence_score=None)

        rendered = RadiologySummaryService().render(result, RadiologyOutputFormat.TEXT)

        assert "Not provided." in rendered
