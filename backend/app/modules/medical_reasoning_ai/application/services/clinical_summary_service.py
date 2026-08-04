"""`ClinicalSummaryService` — this task's own explicitly-named
APPLICATION service, doubling as this module's "Shared renderer" (per
this task's own REUSE section) — the same rendering role
`app.modules.differential_diagnosis_ai.application.services
.differential_diagnosis_renderer.DifferentialDiagnosisRenderer` fills
for its own module, plus a deterministic executive-summary helper that
makes it more than a pure formatter (earning its "Clinical Summary
Service" name).

No use case wraps `render` — this task's own APPLICATION section names
`GenerateClinicalReasoningUseCase` as the only use case, so
`public/facade.py::MedicalReasoningAIFacade.render_result` calls this
service directly, the same choice
`app.modules.differential_diagnosis_ai.public.facade
.DifferentialDiagnosisAIFacade` makes for its own renderer.
"""

import json

from app.modules.medical_reasoning_ai.domain.enums import MedicalReasoningOutputFormat
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    MedicalReasoningResult,
    RedFlag,
)


class ClinicalSummaryService:
    def summarize(self, result: MedicalReasoningResult) -> str:
        """A short, deterministic "at a glance" digest — combines the
        AI's own `clinical_summary` with evidence/red-flag counts, useful
        anywhere a full rendered result is too much (e.g. an audit trail
        or a list view a future consumer module builds)."""
        return (
            f"{result.clinical_summary} "
            f"({len(result.supporting_evidence)} supporting, "
            f"{len(result.contradicting_evidence)} contradicting, "
            f"{len(result.red_flags)} red flag(s))"
        )

    def render(
        self, result: MedicalReasoningResult, target_format: MedicalReasoningOutputFormat
    ) -> str:
        if target_format is MedicalReasoningOutputFormat.JSON:
            return self._render_json(result)
        if target_format is MedicalReasoningOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: MedicalReasoningResult) -> str:
        payload = {
            "clinical_summary": result.clinical_summary,
            "evidence": [
                {
                    "description": item.description,
                    "weight": item.weight,
                    "polarity": item.polarity.value,
                }
                for item in result.evidence
            ],
            "missing_information": list(result.missing_information),
            "clinical_confidence": result.clinical_confidence,
            "diagnostic_confidence": result.diagnostic_confidence,
            "therapeutic_confidence": result.therapeutic_confidence,
            "risk_factors": list(result.risk_factors),
            "red_flags": [
                {"description": flag.description, "priority": flag.priority.value}
                for flag in result.red_flags
            ],
            "suggested_next_questions": list(result.suggested_next_questions),
            "suggested_investigations": list(result.suggested_investigations),
            "suggested_monitoring": list(result.suggested_monitoring),
            "clinical_justification": result.clinical_justification,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_markdown(self, result: MedicalReasoningResult) -> str:
        sections = [f"## Clinical Summary\n\n{result.clinical_summary}"]
        if result.supporting_evidence:
            sections.append(
                "## Supporting Evidence\n\n"
                + "\n".join(self._render_evidence_line(item) for item in result.supporting_evidence)
            )
        if result.contradicting_evidence:
            sections.append(
                "## Contradicting Evidence\n\n"
                + "\n".join(
                    self._render_evidence_line(item) for item in result.contradicting_evidence
                )
            )
        if result.missing_information:
            sections.append(
                "## Missing Information\n\n"
                + "\n".join(f"- {item}" for item in result.missing_information)
            )
        sections.append(
            "## Confidence\n\n"
            f"- **Clinical:** {self._format_confidence(result.clinical_confidence)}\n"
            f"- **Diagnostic:** {self._format_confidence(result.diagnostic_confidence)}\n"
            f"- **Therapeutic:** {self._format_confidence(result.therapeutic_confidence)}"
        )
        if result.risk_factors:
            sections.append(
                "## Risk Factors\n\n" + "\n".join(f"- {item}" for item in result.risk_factors)
            )
        if result.red_flags:
            sections.append(
                "## Red Flags\n\n"
                + "\n".join(self._render_red_flag_line(flag) for flag in result.red_flags)
            )
        if result.suggested_next_questions:
            sections.append(
                "## Suggested Next Questions\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_next_questions)
            )
        if result.suggested_investigations:
            sections.append(
                "## Suggested Investigations\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_investigations)
            )
        if result.suggested_monitoring:
            sections.append(
                "## Suggested Monitoring\n\n"
                + "\n".join(f"- {item}" for item in result.suggested_monitoring)
            )
        sections.append(f"## Clinical Justification\n\n{result.clinical_justification}")
        return "\n\n".join(sections)

    def _render_evidence_line(self, item: EvidenceItem) -> str:
        return f"- {item.description} (weight: {item.weight:.2f})"

    def _render_red_flag_line(self, flag: RedFlag) -> str:
        return f"- [{flag.priority.value.upper()}] {flag.description}"

    def _render_text(self, result: MedicalReasoningResult) -> str:
        sections = [f"CLINICAL SUMMARY:\n{result.clinical_summary}"]
        if result.supporting_evidence:
            sections.append(
                "SUPPORTING EVIDENCE:\n"
                + "\n".join(self._render_evidence_line(item) for item in result.supporting_evidence)
            )
        if result.contradicting_evidence:
            sections.append(
                "CONTRADICTING EVIDENCE:\n"
                + "\n".join(
                    self._render_evidence_line(item) for item in result.contradicting_evidence
                )
            )
        if result.missing_information:
            sections.append(
                "MISSING INFORMATION:\n"
                + "\n".join(f"- {item}" for item in result.missing_information)
            )
        sections.append(
            "CONFIDENCE:\n"
            f"Clinical: {self._format_confidence(result.clinical_confidence)}\n"
            f"Diagnostic: {self._format_confidence(result.diagnostic_confidence)}\n"
            f"Therapeutic: {self._format_confidence(result.therapeutic_confidence)}"
        )
        if result.risk_factors:
            sections.append(
                "RISK FACTORS:\n" + "\n".join(f"- {item}" for item in result.risk_factors)
            )
        if result.red_flags:
            sections.append(
                "RED FLAGS:\n"
                + "\n".join(self._render_red_flag_line(flag) for flag in result.red_flags)
            )
        if result.suggested_next_questions:
            sections.append(
                "SUGGESTED NEXT QUESTIONS:\n"
                + "\n".join(f"- {item}" for item in result.suggested_next_questions)
            )
        if result.suggested_investigations:
            sections.append(
                "SUGGESTED INVESTIGATIONS:\n"
                + "\n".join(f"- {item}" for item in result.suggested_investigations)
            )
        if result.suggested_monitoring:
            sections.append(
                "SUGGESTED MONITORING:\n"
                + "\n".join(f"- {item}" for item in result.suggested_monitoring)
            )
        sections.append(f"CLINICAL JUSTIFICATION:\n{result.clinical_justification}")
        return "\n\n".join(sections)

    def _format_confidence(self, confidence: float | None) -> str:
        return "Not provided." if confidence is None else f"{confidence:.2f}"
