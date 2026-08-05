"""`RadiologySummaryService` — this task's own explicitly-named
APPLICATION service, doubling as this module's "Shared renderer" (per
this task's own REUSE section) — the same rendering role every prior AI
module's own summary/renderer service fills for itself, plus a
deterministic executive-summary helper that makes it more than a pure
formatter (earning its "Radiology Summary Service" name, the same shape
`app.modules.medical_reasoning_ai.application.services
.clinical_summary_service.ClinicalSummaryService.summarize` establishes
for its own module).

No use case wraps `render`/`summarize` — this task's own APPLICATION
section names `InterpretRadiologyReportUseCase` as the only use case, so
`public/facade.py::RadiologyInterpretationAIFacade.render_result` calls
this service directly, the same choice every prior AI module's own
facade makes for its own renderer.
"""

import json

from app.modules.radiology_interpretation_ai.domain.enums import RadiologyOutputFormat
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyFinding,
    RadiologyInterpretationResult,
)


class RadiologySummaryService:
    def summarize(self, result: RadiologyInterpretationResult) -> str:
        """A short, deterministic "at a glance" digest — combines the
        AI's own `examination_summary` with finding/red-flag counts,
        useful anywhere a full rendered result is too much (e.g. an
        audit trail or a list view a future consumer module builds)."""
        return (
            f"{result.examination_summary} "
            f"({len(result.abnormal_findings)} abnormal, "
            f"{len(result.critical_findings)} critical, "
            f"{len(result.incidental_findings)} incidental, "
            f"{len(result.red_flag_warnings)} red flag(s))"
        )

    def render(
        self, result: RadiologyInterpretationResult, target_format: RadiologyOutputFormat
    ) -> str:
        if target_format is RadiologyOutputFormat.JSON:
            return self._render_json(result)
        if target_format is RadiologyOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: RadiologyInterpretationResult) -> str:
        payload = {
            "examination_summary": result.examination_summary,
            "findings": [self._finding_dict(finding) for finding in result.findings],
            "clinical_significance": result.clinical_significance,
            "differential_imaging_considerations": list(result.differential_imaging_considerations),
            "suggested_follow_up_imaging": list(result.suggested_follow_up_imaging),
            "suggested_specialist_referral": list(result.suggested_specialist_referral),
            "red_flag_warnings": list(result.red_flag_warnings),
            "confidence_score": result.confidence_score,
            "clinical_reasoning": result.clinical_reasoning,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _finding_dict(self, finding: RadiologyFinding) -> dict[str, object]:
        return {
            "description": finding.description,
            "category": finding.category.value,
            "anatomical_region": finding.anatomical_region,
        }

    def _render_finding_line(self, finding: RadiologyFinding) -> str:
        region_suffix = f" ({finding.anatomical_region})" if finding.anatomical_region else ""
        return f"- {finding.description}{region_suffix} [{finding.category.value}]"

    def _render_markdown(self, result: RadiologyInterpretationResult) -> str:
        sections = [f"## Examination Summary\n\n{result.examination_summary}"]
        if result.important_findings:
            sections.append(
                "## Important Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.important_findings)
            )
        if result.normal_findings:
            sections.append(
                "## Normal Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.normal_findings)
            )
        if result.abnormal_findings:
            sections.append(
                "## Abnormal Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.abnormal_findings)
            )
        if result.incidental_findings:
            sections.append(
                "## Incidental Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.incidental_findings)
            )
        if result.critical_findings:
            sections.append(
                "## Critical Findings\n\n"
                + "\n".join(self._render_finding_line(f) for f in result.critical_findings)
            )
        if result.clinical_significance.strip():
            sections.append(f"## Possible Clinical Significance\n\n{result.clinical_significance}")
        if result.differential_imaging_considerations:
            sections.append(
                "## Differential Imaging Considerations\n\n"
                + "\n".join(f"- {item}" for item in result.differential_imaging_considerations)
            )
        if result.suggested_follow_up_imaging:
            sections.append(
                "## Suggested Follow-up Imaging\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up_imaging)
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

    def _render_text(self, result: RadiologyInterpretationResult) -> str:
        sections = [f"EXAMINATION SUMMARY:\n{result.examination_summary}"]
        if result.important_findings:
            sections.append(
                "IMPORTANT FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.important_findings)
            )
        if result.normal_findings:
            sections.append(
                "NORMAL FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.normal_findings)
            )
        if result.abnormal_findings:
            sections.append(
                "ABNORMAL FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.abnormal_findings)
            )
        if result.incidental_findings:
            sections.append(
                "INCIDENTAL FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.incidental_findings)
            )
        if result.critical_findings:
            sections.append(
                "CRITICAL FINDINGS:\n"
                + "\n".join(self._render_finding_line(f) for f in result.critical_findings)
            )
        if result.clinical_significance.strip():
            sections.append(f"POSSIBLE CLINICAL SIGNIFICANCE:\n{result.clinical_significance}")
        if result.differential_imaging_considerations:
            sections.append(
                "DIFFERENTIAL IMAGING CONSIDERATIONS:\n"
                + "\n".join(f"- {item}" for item in result.differential_imaging_considerations)
            )
        if result.suggested_follow_up_imaging:
            sections.append(
                "SUGGESTED FOLLOW-UP IMAGING:\n"
                + "\n".join(f"- {item}" for item in result.suggested_follow_up_imaging)
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
