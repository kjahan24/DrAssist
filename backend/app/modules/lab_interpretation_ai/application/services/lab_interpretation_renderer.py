"""`LabInterpretationRenderer` — this module's own "Shared renderer" (per
this task's own REUSE section) and the JSON/Markdown/Plain-text
implementation this task's own OUTPUT section requires.

Unlike `app.modules.medical_reasoning_ai.application.services
.clinical_summary_service.ClinicalSummaryService`, none of this task's
four explicitly-named APPLICATION services (`InterpretLabResultsUseCase`,
`CriticalValueDetectionService`, `LabTrendAnalysisService`,
`LabRecommendationService`) is naturally a renderer, so this small,
fifth service is added as the same "named [items] plus the
operationally-necessary rest" precedent every prior AI module's own
`application/ports.py` documents for its port list, applied here to this
module's application services instead — a required capability this
task's own OUTPUT section names ("Support: JSON, Markdown, Plain text")
has to live *somewhere*, and a renderer is application-layer formatting
logic, not a use case or a port-backed capability, the same placement
choice `ClinicalSummaryService`/every prior AI module's own renderer
already establishes.

No use case wraps `render` — `public/facade.py
::LabInterpretationAIFacade.render_result` calls this service directly,
the same choice every prior AI module's own facade makes for its own
renderer.
"""

import json

from app.modules.lab_interpretation_ai.domain.enums import LabInterpretationOutputFormat
from app.modules.lab_interpretation_ai.domain.value_objects import (
    LabFinding,
    LabInterpretationResult,
)


class LabInterpretationRenderer:
    def render(
        self, result: LabInterpretationResult, target_format: LabInterpretationOutputFormat
    ) -> str:
        if target_format is LabInterpretationOutputFormat.JSON:
            return self._render_json(result)
        if target_format is LabInterpretationOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: LabInterpretationResult) -> str:
        payload = {
            "overall_interpretation": result.overall_interpretation,
            "findings": [self._finding_dict(finding) for finding in result.findings],
            "clinical_significance": result.clinical_significance,
            "supporting_evidence": list(result.supporting_evidence),
            "potential_causes": list(result.potential_causes),
            "suggested_follow_up_tests": list(result.suggested_follow_up_tests),
            "monitoring_recommendations": list(result.monitoring_recommendations),
            "red_flag_warnings": list(result.red_flag_warnings),
            "confidence_score": result.confidence_score,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _finding_dict(self, finding: LabFinding) -> dict[str, object]:
        return {
            "test_name": finding.test_name,
            "value": finding.value,
            "numeric_value": finding.numeric_value,
            "unit": finding.unit,
            "flag": finding.flag.value,
        }

    def _render_finding_line(self, finding: LabFinding) -> str:
        unit_suffix = f" {finding.unit}" if finding.unit else ""
        return f"- {finding.test_name}: {finding.value}{unit_suffix} [{finding.flag.value}]"

    def _render_markdown(self, result: LabInterpretationResult) -> str:
        sections = [f"## Overall Interpretation\n\n{result.overall_interpretation}"]
        if result.abnormal_findings:
            sections.append(
                "## Abnormal Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.abnormal_findings)
            )
        if result.critical_values:
            sections.append(
                "## Critical Values\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.critical_values)
            )
        if result.clinical_significance.strip():
            sections.append(f"## Possible Clinical Significance\n\n{result.clinical_significance}")
        if result.supporting_evidence:
            sections.append(
                "## Supporting Evidence\n\n"
                + "\n".join(f"- {item}" for item in result.supporting_evidence)
            )
        if result.potential_causes:
            sections.append(
                "## Potential Causes\n\n"
                + "\n".join(f"- {item}" for item in result.potential_causes)
            )
        if result.suggested_follow_up_tests:
            sections.append(
                "## Suggested Follow-up Tests\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up_tests)
            )
        if result.monitoring_recommendations:
            sections.append(
                "## Monitoring Recommendations\n\n"
                + "\n".join(f"- {item}" for item in result.monitoring_recommendations)
            )
        if result.red_flag_warnings:
            sections.append(
                "## Red Flag Warnings\n\n"
                + "\n".join(f"- {item}" for item in result.red_flag_warnings)
            )
        sections.append(
            f"## Confidence Score\n\n{self._format_confidence(result.confidence_score)}"
        )
        return "\n\n".join(sections)

    def _render_text(self, result: LabInterpretationResult) -> str:
        sections = [f"OVERALL INTERPRETATION:\n{result.overall_interpretation}"]
        if result.abnormal_findings:
            sections.append(
                "ABNORMAL FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.abnormal_findings)
            )
        if result.critical_values:
            sections.append(
                "CRITICAL VALUES:\n"
                + "\n".join(self._render_finding_line(f) for f in result.critical_values)
            )
        if result.clinical_significance.strip():
            sections.append(f"POSSIBLE CLINICAL SIGNIFICANCE:\n{result.clinical_significance}")
        if result.supporting_evidence:
            sections.append(
                "SUPPORTING EVIDENCE:\n"
                + "\n".join(f"- {item}" for item in result.supporting_evidence)
            )
        if result.potential_causes:
            sections.append(
                "POTENTIAL CAUSES:\n" + "\n".join(f"- {item}" for item in result.potential_causes)
            )
        if result.suggested_follow_up_tests:
            sections.append(
                "SUGGESTED FOLLOW-UP TESTS:\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up_tests)
            )
        if result.monitoring_recommendations:
            sections.append(
                "MONITORING RECOMMENDATIONS:\n"
                + "\n".join(f"- {item}" for item in result.monitoring_recommendations)
            )
        if result.red_flag_warnings:
            sections.append(
                "RED FLAG WARNINGS:\n" + "\n".join(f"- {item}" for item in result.red_flag_warnings)
            )
        sections.append(f"CONFIDENCE SCORE:\n{self._format_confidence(result.confidence_score)}")
        return "\n\n".join(sections)

    def _format_confidence(self, confidence: float | None) -> str:
        return "Not provided." if confidence is None else f"{confidence:.2f}"
