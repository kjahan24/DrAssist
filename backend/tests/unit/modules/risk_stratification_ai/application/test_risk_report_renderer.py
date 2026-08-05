"""Tests for `RiskReportRenderer`."""

import json

from app.modules.risk_stratification_ai.application.services.risk_report_renderer import (
    RiskReportRenderer,
)
from app.modules.risk_stratification_ai.domain.enums import (
    OverallRiskLevel,
    RiskStratificationOutputFormat,
)
from tests.unit.modules.risk_stratification_ai.application.fakes import make_result, make_risk_score


class TestSummarize:
    def test_includes_overall_risk_level(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result(overall_risk_level=OverallRiskLevel.HIGH)

        summary = renderer.summarize(result)

        assert "high" in summary

    def test_includes_risk_score_and_red_flag_counts(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result(
            risk_scores=(make_risk_score(),), red_flag_alerts=("Critical NEWS2 score",)
        )

        summary = renderer.summarize(result)

        assert "1 risk score(s)" in summary
        assert "1 red flag(s)" in summary


class TestRenderJson:
    def test_produces_valid_json(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result()

        rendered = renderer.render(result, RiskStratificationOutputFormat.JSON)
        payload = json.loads(rendered)

        assert payload["overall_risk_level"] == result.overall_risk_level.value
        assert payload["confidence_score"] == result.confidence_score

    def test_includes_risk_score_details(self) -> None:
        renderer = RiskReportRenderer()
        score = make_risk_score(score_value=5.0, contributing_factors=("Tachycardia",))
        result = make_result(risk_scores=(score,))

        payload = json.loads(renderer.render(result, RiskStratificationOutputFormat.JSON))

        assert payload["risk_scores"][0]["category"] == score.category.value
        assert payload["risk_scores"][0]["score_value"] == 5.0
        assert payload["risk_scores"][0]["contributing_factors"] == ["Tachycardia"]


class TestRenderMarkdown:
    def test_includes_overall_risk_level_heading(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result()

        rendered = renderer.render(result, RiskStratificationOutputFormat.MARKDOWN)

        assert "## Overall Risk Level" in rendered

    def test_omits_empty_sections(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result(risk_scores=(), red_flag_alerts=())

        rendered = renderer.render(result, RiskStratificationOutputFormat.MARKDOWN)

        assert "## Risk Scores" not in rendered
        assert "## Red Flag Alerts" not in rendered

    def test_includes_populated_sections(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result(
            red_flag_alerts=("SpO2 88%",),
            recommended_monitoring=("Monitor SpO2",),
            suggested_escalation=("Urgent review",),
            suggested_follow_up=("Pulmonology follow-up",),
        )

        rendered = renderer.render(result, RiskStratificationOutputFormat.MARKDOWN)

        assert "## Red Flag Alerts" in rendered
        assert "## Recommended Monitoring" in rendered
        assert "## Suggested Escalation" in rendered
        assert "## Suggested Follow-up" in rendered

    def test_includes_clinical_reasoning_when_present(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result(clinical_reasoning="Grounded reasoning.")

        rendered = renderer.render(result, RiskStratificationOutputFormat.MARKDOWN)

        assert "## Clinical Reasoning" in rendered


class TestRenderText:
    def test_includes_overall_risk_level_label(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result()

        rendered = renderer.render(result, RiskStratificationOutputFormat.TEXT)

        assert "OVERALL RISK LEVEL:" in rendered

    def test_confidence_not_provided_when_none(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result(confidence_score=None)

        rendered = renderer.render(result, RiskStratificationOutputFormat.TEXT)

        assert "Not provided." in rendered

    def test_confidence_formatted_when_present(self) -> None:
        renderer = RiskReportRenderer()
        result = make_result(confidence_score=0.87)

        rendered = renderer.render(result, RiskStratificationOutputFormat.TEXT)

        assert "0.87" in rendered
