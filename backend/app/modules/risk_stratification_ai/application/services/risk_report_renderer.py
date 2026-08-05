"""`RiskReportRenderer` — this module's own "Shared renderer" (per this
task's own REUSE section) and the JSON/Markdown/Plain-text
implementation this task's own OUTPUT section requires ("Support: JSON,
Markdown, Plain text").

This task's own APPLICATION section does not name a renderer among its
five explicit services (`AnalyzePatientRiskUseCase`, `RiskScoringService`,
`EarlyWarningService`, `RiskExplanationService`,
`MonitoringRecommendationService`) — so this service is added as the
same "named [items] plus the operationally-necessary rest" precedent
every prior AI module's own `application/services` list documents for
itself (most recently `app.modules.drug_interaction_ai.application
.services.drug_safety_report_renderer.DrugSafetyReportRenderer`, whose
own task also named no renderer explicitly).

No use case wraps `render` — `public/facade.py
::RiskStratificationAIFacade.render_result` calls this service directly,
the same choice every prior AI module's own facade makes for its own
renderer.
"""

import json

from app.modules.risk_stratification_ai.domain.enums import RiskStratificationOutputFormat
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskScore,
    RiskStratificationResult,
)


class RiskReportRenderer:
    def summarize(self, result: RiskStratificationResult) -> str:
        """A short, deterministic "at a glance" digest — the overall
        risk level plus counts of red flags and risk scores, useful
        anywhere a full rendered result is too much (e.g. an audit trail
        or a list view a future consumer module builds)."""
        return (
            f"Overall risk: {result.overall_risk_level.value} "
            f"({len(result.risk_scores)} risk score(s), "
            f"{len(result.red_flag_alerts)} red flag(s))"
        )

    def render(
        self, result: RiskStratificationResult, target_format: RiskStratificationOutputFormat
    ) -> str:
        if target_format is RiskStratificationOutputFormat.JSON:
            return self._render_json(result)
        if target_format is RiskStratificationOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: RiskStratificationResult) -> str:
        payload = {
            "overall_risk_level": result.overall_risk_level.value,
            "risk_scores": [self._score_dict(score) for score in result.risk_scores],
            "early_warning_indicators": list(result.early_warning_indicators),
            "recommended_monitoring": list(result.recommended_monitoring),
            "suggested_escalation": list(result.suggested_escalation),
            "suggested_follow_up": list(result.suggested_follow_up),
            "red_flag_alerts": list(result.red_flag_alerts),
            "clinical_reasoning": result.clinical_reasoning,
            "confidence_score": result.confidence_score,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _score_dict(self, score: RiskScore) -> dict[str, object]:
        return {
            "category": score.category.value,
            "score_value": score.score_value,
            "contributing_factors": list(score.contributing_factors),
            "clinical_explanation": score.clinical_explanation,
        }

    def _render_score_line(self, score: RiskScore) -> str:
        value_suffix = f" = {score.score_value:g}" if score.score_value is not None else ""
        return f"- {score.category.value}{value_suffix}: {score.clinical_explanation}"

    def _render_markdown(self, result: RiskStratificationResult) -> str:
        sections = [f"## Overall Risk Level\n\n{result.overall_risk_level.value}"]
        if result.risk_scores:
            sections.append(
                "## Risk Scores\n\n"
                + "\n".join(self._render_score_line(score) for score in result.risk_scores)
            )
        if result.early_warning_indicators:
            sections.append(
                "## Early Warning Indicators\n\n"
                + "\n".join(f"- {item}" for item in result.early_warning_indicators)
            )
        if result.red_flag_alerts:
            sections.append(
                "## Red Flag Alerts\n\n" + "\n".join(f"- {item}" for item in result.red_flag_alerts)
            )
        if result.recommended_monitoring:
            sections.append(
                "## Recommended Monitoring\n\n"
                + "\n".join(f"- {item}" for item in result.recommended_monitoring)
            )
        if result.suggested_escalation:
            sections.append(
                "## Suggested Escalation\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_escalation)
            )
        if result.suggested_follow_up:
            sections.append(
                "## Suggested Follow-up\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up)
            )
        sections.append(
            f"## Confidence Score\n\n{self._format_confidence(result.confidence_score)}"
        )
        if result.clinical_reasoning.strip():
            sections.append(f"## Clinical Reasoning\n\n{result.clinical_reasoning}")
        return "\n\n".join(sections)

    def _render_text(self, result: RiskStratificationResult) -> str:
        sections = [f"OVERALL RISK LEVEL:\n{result.overall_risk_level.value}"]
        if result.risk_scores:
            sections.append(
                "RISK SCORES:\n"
                + "\n".join(self._render_score_line(score) for score in result.risk_scores)
            )
        if result.early_warning_indicators:
            sections.append(
                "EARLY WARNING INDICATORS:\n"
                + "\n".join(f"- {item}" for item in result.early_warning_indicators)
            )
        if result.red_flag_alerts:
            sections.append(
                "RED FLAG ALERTS:\n" + "\n".join(f"- {item}" for item in result.red_flag_alerts)
            )
        if result.recommended_monitoring:
            sections.append(
                "RECOMMENDED MONITORING:\n"
                + "\n".join(f"- {item}" for item in result.recommended_monitoring)
            )
        if result.suggested_escalation:
            sections.append(
                "SUGGESTED ESCALATION:\n"
                + "\n".join(f"- {item}" for item in result.suggested_escalation)
            )
        if result.suggested_follow_up:
            sections.append(
                "SUGGESTED FOLLOW-UP:\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up)
            )
        sections.append(f"CONFIDENCE SCORE:\n{self._format_confidence(result.confidence_score)}")
        if result.clinical_reasoning.strip():
            sections.append(f"CLINICAL REASONING:\n{result.clinical_reasoning}")
        return "\n\n".join(sections)

    def _format_confidence(self, confidence: float | None) -> str:
        return "Not provided." if confidence is None else f"{confidence:.2f}"
