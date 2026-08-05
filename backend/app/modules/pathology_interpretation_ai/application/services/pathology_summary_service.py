"""`PathologySummaryService` — this task's own explicitly-named
APPLICATION service, doubling as this module's "Shared renderer" (per
this task's own REUSE section) — the same rendering role every prior AI
module's own summary/renderer service fills for itself, plus a
deterministic executive-summary helper that makes it more than a pure
formatter (earning its "Pathology Summary Service" name, the same shape
`app.modules.medical_reasoning_ai.application.services
.clinical_summary_service.ClinicalSummaryService.summarize` establishes
for its own module).

No use case wraps `render`/`summarize` — this task's own APPLICATION
section names `InterpretPathologyReportUseCase` as the only use case, so
`public/facade.py::PathologyInterpretationAIFacade.render_result` calls
this service directly, the same choice every prior AI module's own
facade makes for its own renderer.
"""

import json

from app.modules.pathology_interpretation_ai.domain.enums import PathologyOutputFormat
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyFinding,
    PathologyInterpretationResult,
)


class PathologySummaryService:
    def summarize(self, result: PathologyInterpretationResult) -> str:
        """A short, deterministic "at a glance" digest — combines the
        AI's own `pathology_summary` with finding/red-flag counts,
        useful anywhere a full rendered result is too much (e.g. an
        audit trail or a list view a future consumer module builds)."""
        return (
            f"{result.pathology_summary} "
            f"({len(result.malignant_features)} malignant, "
            f"{len(result.atypical_findings)} atypical, "
            f"{len(result.benign_features)} benign, "
            f"{len(result.red_flag_warnings)} red flag(s))"
        )

    def render(
        self, result: PathologyInterpretationResult, target_format: PathologyOutputFormat
    ) -> str:
        if target_format is PathologyOutputFormat.JSON:
            return self._render_json(result)
        if target_format is PathologyOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: PathologyInterpretationResult) -> str:
        payload = {
            "pathology_summary": result.pathology_summary,
            "key_findings": list(result.key_findings),
            "microscopic_findings": [
                self._finding_dict(finding) for finding in result.microscopic_findings
            ],
            "final_impression": result.final_impression,
            "clinical_significance": result.clinical_significance,
            "correlation_recommendations": list(result.correlation_recommendations),
            "suggested_follow_up": list(result.suggested_follow_up),
            "suggested_specialist_referral": list(result.suggested_specialist_referral),
            "red_flag_warnings": list(result.red_flag_warnings),
            "confidence_score": result.confidence_score,
            "clinical_reasoning": result.clinical_reasoning,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _finding_dict(self, finding: PathologyFinding) -> dict[str, object]:
        return {
            "description": finding.description,
            "category": finding.category.value,
            "anatomical_site": finding.anatomical_site,
        }

    def _render_finding_line(self, finding: PathologyFinding) -> str:
        site_suffix = f" ({finding.anatomical_site})" if finding.anatomical_site else ""
        return f"- {finding.description}{site_suffix} [{finding.category.value}]"

    def _render_markdown(self, result: PathologyInterpretationResult) -> str:
        sections = [f"## Pathology Summary\n\n{result.pathology_summary}"]
        if result.key_findings:
            sections.append(
                "## Key Findings\n\n" + "\n".join(f"- {item}" for item in result.key_findings)
            )
        if result.microscopic_findings:
            sections.append(
                "## Microscopic Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.microscopic_findings)
            )
        if result.benign_features:
            sections.append(
                "## Benign Features\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.benign_features)
            )
        if result.malignant_features:
            sections.append(
                "## Malignant Features\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.malignant_features)
            )
        if result.atypical_findings:
            sections.append(
                "## Atypical Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.atypical_findings)
            )
        if result.final_impression.strip():
            sections.append(f"## Final Impression\n\n{result.final_impression}")
        if result.clinical_significance.strip():
            sections.append(f"## Possible Clinical Significance\n\n{result.clinical_significance}")
        if result.correlation_recommendations:
            sections.append(
                "## Correlation Recommendations\n\n"
                + "\n".join(f"- {item}" for item in result.correlation_recommendations)
            )
        if result.suggested_follow_up:
            sections.append(
                "## Suggested Follow-up\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up)
            )
        if result.suggested_specialist_referral:
            sections.append(
                "## Suggested Specialist Referral\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_specialist_referral)
            )
        if result.red_flag_warnings:
            sections.append(
                "## Red Flag Warnings\n\n"
                + "\n".join(f"- {item}" for item in result.red_flag_warnings)
            )
        sections.append(
            f"## Confidence Score\n\n{self._format_confidence(result.confidence_score)}"
        )
        if result.clinical_reasoning.strip():
            sections.append(f"## Clinical Reasoning\n\n{result.clinical_reasoning}")
        return "\n\n".join(sections)

    def _render_text(self, result: PathologyInterpretationResult) -> str:
        sections = [f"PATHOLOGY SUMMARY:\n{result.pathology_summary}"]
        if result.key_findings:
            sections.append(
                "KEY FINDINGS:\n" + "\n".join(f"- {item}" for item in result.key_findings)
            )
        if result.microscopic_findings:
            sections.append(
                "MICROSCOPIC FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.microscopic_findings)
            )
        if result.benign_features:
            sections.append(
                "BENIGN FEATURES:\n"
                + "\n".join(self._render_finding_line(f) for f in result.benign_features)
            )
        if result.malignant_features:
            sections.append(
                "MALIGNANT FEATURES:\n"
                + "\n".join(self._render_finding_line(f) for f in result.malignant_features)
            )
        if result.atypical_findings:
            sections.append(
                "ATYPICAL FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.atypical_findings)
            )
        if result.final_impression.strip():
            sections.append(f"FINAL IMPRESSION:\n{result.final_impression}")
        if result.clinical_significance.strip():
            sections.append(f"POSSIBLE CLINICAL SIGNIFICANCE:\n{result.clinical_significance}")
        if result.correlation_recommendations:
            sections.append(
                "CORRELATION RECOMMENDATIONS:\n"
                + "\n".join(f"- {item}" for item in result.correlation_recommendations)
            )
        if result.suggested_follow_up:
            sections.append(
                "SUGGESTED FOLLOW-UP:\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up)
            )
        if result.suggested_specialist_referral:
            sections.append(
                "SUGGESTED SPECIALIST REFERRAL:\n"
                + "\n".join(f"- {item}" for item in result.suggested_specialist_referral)
            )
        if result.red_flag_warnings:
            sections.append(
                "RED FLAG WARNINGS:\n" + "\n".join(f"- {item}" for item in result.red_flag_warnings)
            )
        sections.append(f"CONFIDENCE SCORE:\n{self._format_confidence(result.confidence_score)}")
        if result.clinical_reasoning.strip():
            sections.append(f"CLINICAL REASONING:\n{result.clinical_reasoning}")
        return "\n\n".join(sections)

    def _format_confidence(self, confidence: float | None) -> str:
        return "Not provided." if confidence is None else f"{confidence:.2f}"
