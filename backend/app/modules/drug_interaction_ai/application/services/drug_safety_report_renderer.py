"""`DrugSafetyReportRenderer` — this module's own "Shared renderer" (per
this task's own REUSE section) and the JSON/Markdown/Plain-text
implementation this task's own OUTPUT section requires ("Support: JSON,
Markdown, Plain text").

Unlike `app.modules.pathology_interpretation_ai.application.services
.pathology_summary_service.PathologySummaryService`, this task's own
APPLICATION section does not name a renderer among its six explicit
services (`AnalyzeMedicationSafetyUseCase`, `DrugInteractionService`,
`MedicationSafetyService`, `ContraindicationService`,
`DoseAdjustmentService`, `AlternativeMedicationService`) — so this small,
seventh service is added as the same "named [items] plus the
operationally-necessary rest" precedent every prior AI module's own
`application/ports.py`/`application/services` list documents for itself
(most recently
`app.modules.radiology_interpretation_ai.application.services
.radiology_summary_service.RadiologySummaryService`, whose own task also
named no renderer explicitly), applied here to application services
instead of ports: a required capability this task's own OUTPUT section
names has to live *somewhere*, and rendering is application-layer
formatting logic, not a use case or a port-backed capability.

No use case wraps `render` — `public/facade.py
::DrugInteractionAIFacade.render_result` calls this service directly,
the same choice every prior AI module's own facade makes for its own
renderer.
"""

import json

from app.modules.drug_interaction_ai.domain.enums import DrugInteractionOutputFormat
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisResult,
    SafetyIssue,
)


class DrugSafetyReportRenderer:
    def summarize(self, result: DrugInteractionAnalysisResult) -> str:
        """A short, deterministic "at a glance" digest — combines the
        AI's own `safety_summary` with interaction/contraindication
        counts, useful anywhere a full rendered result is too much (e.g.
        an audit trail or a list view a future consumer module
        builds)."""
        return (
            f"{result.safety_summary} "
            f"({len(result.interactions)} interaction(s), "
            f"{len(result.contraindications)} contraindication(s), "
            f"{len(result.warnings)} warning(s))"
        )

    def render(
        self, result: DrugInteractionAnalysisResult, target_format: DrugInteractionOutputFormat
    ) -> str:
        if target_format is DrugInteractionOutputFormat.JSON:
            return self._render_json(result)
        if target_format is DrugInteractionOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: DrugInteractionAnalysisResult) -> str:
        payload = {
            "safety_summary": result.safety_summary,
            "interactions": [self._issue_dict(issue) for issue in result.interactions],
            "contraindications": list(result.contraindications),
            "warnings": list(result.warnings),
            "monitoring_recommendations": list(result.monitoring_recommendations),
            "dose_adjustment_suggestions": list(result.dose_adjustment_suggestions),
            "alternative_medication_suggestions": list(result.alternative_medication_suggestions),
            "patient_counseling_points": list(result.patient_counseling_points),
            "confidence_score": result.confidence_score,
            "clinical_reasoning": result.clinical_reasoning,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _issue_dict(self, issue: SafetyIssue) -> dict[str, object]:
        return {
            "category": issue.category.value,
            "description": issue.description,
            "severity": issue.severity.value,
            "mechanism": issue.mechanism,
            "clinical_significance": issue.clinical_significance,
            "evidence_level": issue.evidence_level.value if issue.evidence_level else None,
            "involved_medications": list(issue.involved_medications),
        }

    def _render_issue_line(self, issue: SafetyIssue) -> str:
        evidence_suffix = (
            f", evidence: {issue.evidence_level.value}" if issue.evidence_level else ""
        )
        return (
            f"- {issue.description} "
            f"[{issue.category.value}, {issue.severity.value}{evidence_suffix}]"
        )

    def _render_markdown(self, result: DrugInteractionAnalysisResult) -> str:
        sections = [f"## Medication Safety Summary\n\n{result.safety_summary}"]
        if result.interactions:
            sections.append(
                "## Interaction List\n\n"
                + "\n".join(self._render_issue_line(i) for i in result.interactions)
            )
        if result.contraindications:
            sections.append(
                "## Contraindications\n\n"
                + "\n".join(f"- {item}" for item in result.contraindications)
            )
        if result.warnings:
            sections.append("## Warnings\n\n" + "\n".join(f"- {item}" for item in result.warnings))
        if result.monitoring_recommendations:
            sections.append(
                "## Monitoring Recommendations\n\n"
                + "\n".join(f"- {item}" for item in result.monitoring_recommendations)
            )
        if result.dose_adjustment_suggestions:
            sections.append(
                "## Dose Adjustment Suggestions\n\n"
                + "\n".join(f"- {item}" for item in result.dose_adjustment_suggestions)
            )
        if result.alternative_medication_suggestions:
            sections.append(
                "## Alternative Medication Suggestions\n\n"
                + "\n".join(f"- {item}" for item in result.alternative_medication_suggestions)
            )
        if result.patient_counseling_points:
            sections.append(
                "## Patient Counseling Points\n\n"
                + "\n".join(f"- {item}" for item in result.patient_counseling_points)
            )
        sections.append(
            f"## Confidence Score\n\n{self._format_confidence(result.confidence_score)}"
        )
        if result.clinical_reasoning.strip():
            sections.append(f"## Clinical Reasoning\n\n{result.clinical_reasoning}")
        return "\n\n".join(sections)

    def _render_text(self, result: DrugInteractionAnalysisResult) -> str:
        sections = [f"MEDICATION SAFETY SUMMARY:\n{result.safety_summary}"]
        if result.interactions:
            sections.append(
                "INTERACTION LIST:\n"
                + "\n".join(self._render_issue_line(i) for i in result.interactions)
            )
        if result.contraindications:
            sections.append(
                "CONTRAINDICATIONS:\n" + "\n".join(f"- {item}" for item in result.contraindications)
            )
        if result.warnings:
            sections.append("WARNINGS:\n" + "\n".join(f"- {item}" for item in result.warnings))
        if result.monitoring_recommendations:
            sections.append(
                "MONITORING RECOMMENDATIONS:\n"
                + "\n".join(f"- {item}" for item in result.monitoring_recommendations)
            )
        if result.dose_adjustment_suggestions:
            sections.append(
                "DOSE ADJUSTMENT SUGGESTIONS:\n"
                + "\n".join(f"- {item}" for item in result.dose_adjustment_suggestions)
            )
        if result.alternative_medication_suggestions:
            sections.append(
                "ALTERNATIVE MEDICATION SUGGESTIONS:\n"
                + "\n".join(f"- {item}" for item in result.alternative_medication_suggestions)
            )
        if result.patient_counseling_points:
            sections.append(
                "PATIENT COUNSELING POINTS:\n"
                + "\n".join(f"- {item}" for item in result.patient_counseling_points)
            )
        sections.append(f"CONFIDENCE SCORE:\n{self._format_confidence(result.confidence_score)}")
        if result.clinical_reasoning.strip():
            sections.append(f"CLINICAL REASONING:\n{result.clinical_reasoning}")
        return "\n\n".join(sections)

    def _format_confidence(self, confidence: float | None) -> str:
        return "Not provided." if confidence is None else f"{confidence:.2f}"
