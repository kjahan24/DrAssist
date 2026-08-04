"""Unit tests for `LabInterpretationRenderer`."""

import json

from app.modules.lab_interpretation_ai.application.services.lab_interpretation_renderer import (
    LabInterpretationRenderer,
)
from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
)
from tests.unit.modules.lab_interpretation_ai.application.fakes import make_finding, make_result


class TestRenderJSON:
    def test_renders_valid_json_with_all_fields(self) -> None:
        result = make_result(
            findings=(make_finding(flag=LabFindingFlag.CRITICAL_HIGH),),
            supporting_evidence=("Glucose markedly elevated",),
        )

        rendered = LabInterpretationRenderer().render(result, LabInterpretationOutputFormat.JSON)

        payload = json.loads(rendered)
        assert payload["overall_interpretation"] == result.overall_interpretation
        assert payload["findings"][0]["flag"] == "critical_high"
        assert payload["supporting_evidence"] == ["Glucose markedly elevated"]
        assert payload["confidence_score"] == result.confidence_score


class TestRenderMarkdown:
    def test_includes_named_sections_that_have_content(self) -> None:
        result = make_result(
            findings=(
                make_finding(test_name="Sodium", flag=LabFindingFlag.ABNORMAL_LOW),
                make_finding(test_name="Glucose", flag=LabFindingFlag.CRITICAL_HIGH),
            ),
            supporting_evidence=("Evidence line",),
            potential_causes=("Possible cause",),
            suggested_follow_up_tests=("Repeat BMP",),
            monitoring_recommendations=("Recheck in 24h",),
            red_flag_warnings=("Critical glucose",),
        )

        rendered = LabInterpretationRenderer().render(
            result, LabInterpretationOutputFormat.MARKDOWN
        )

        assert "## Overall Interpretation" in rendered
        assert "## Abnormal Findings" in rendered
        assert "## Critical Values" in rendered
        assert "## Possible Clinical Significance" in rendered
        assert "## Supporting Evidence" in rendered
        assert "## Potential Causes" in rendered
        assert "## Suggested Follow-up Tests" in rendered
        assert "## Monitoring Recommendations" in rendered
        assert "## Red Flag Warnings" in rendered
        assert "## Confidence Score" in rendered

    def test_omits_optional_sections_when_empty(self) -> None:
        result = make_result(
            findings=(),
            clinical_significance="",
            supporting_evidence=(),
            potential_causes=(),
            suggested_follow_up_tests=(),
            monitoring_recommendations=(),
            red_flag_warnings=(),
        )

        rendered = LabInterpretationRenderer().render(
            result, LabInterpretationOutputFormat.MARKDOWN
        )

        assert "Abnormal Findings" not in rendered
        assert "Critical Values" not in rendered
        assert "Red Flag Warnings" not in rendered


class TestRenderText:
    def test_renders_uppercased_labels(self) -> None:
        result = make_result(red_flag_warnings=("Critical glucose",))

        rendered = LabInterpretationRenderer().render(result, LabInterpretationOutputFormat.TEXT)

        assert "OVERALL INTERPRETATION:" in rendered
        assert "RED FLAG WARNINGS:" in rendered

    def test_formats_missing_confidence_as_not_provided(self) -> None:
        result = make_result(confidence_score=None)

        rendered = LabInterpretationRenderer().render(result, LabInterpretationOutputFormat.TEXT)

        assert "Not provided." in rendered
