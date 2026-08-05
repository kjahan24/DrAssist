"""`PatientEducationReportRenderer` — this module's own "Shared
renderer" (per this task's own REUSE section) and the JSON/Markdown/
Plain-text implementation this task's own OUTPUT section requires
("Support: JSON, Markdown, Plain text").

This task's own APPLICATION section does not name a renderer among its
four explicit items (`GeneratePatientEducationUseCase`,
`PatientEducationService`, `DischargeInstructionService`,
`LifestyleRecommendationService`) — so this service is added as the
same "named [items] plus the operationally-necessary rest" precedent
every prior AI module's own `application/services` list documents for
itself (most recently `app.modules.risk_stratification_ai.application
.services.risk_report_renderer.RiskReportRenderer`, whose own task also
named no renderer explicitly).

No use case wraps `render` — `public/facade.py
::PatientEducationAIFacade.render_result` calls this service directly,
the same choice every prior AI module's own facade makes for its own
renderer.
"""

import json

from app.modules.patient_education_ai.domain.enums import PatientEducationOutputFormat
from app.modules.patient_education_ai.domain.value_objects import PatientEducationResult


class PatientEducationReportRenderer:
    def summarize(self, result: PatientEducationResult) -> str:
        """A short, deterministic "at a glance" digest — the patient
        summary plus counts of medication instructions and warning
        signs, useful anywhere a full rendered result is too much (e.g.
        an audit trail or a list view a future consumer module
        builds)."""
        return (
            f"{result.patient_summary} "
            f"({len(result.medication_instructions)} medication instruction(s), "
            f"{len(result.warning_signs)} warning sign(s))"
        )

    def render(
        self, result: PatientEducationResult, target_format: PatientEducationOutputFormat
    ) -> str:
        if target_format is PatientEducationOutputFormat.JSON:
            return self._render_json(result)
        if target_format is PatientEducationOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: PatientEducationResult) -> str:
        payload = {
            "patient_summary": result.patient_summary,
            "diagnosis_explanation": result.diagnosis_explanation,
            "medication_instructions": list(result.medication_instructions),
            "home_care_plan": list(result.home_care_plan),
            "lifestyle_advice": list(result.lifestyle_advice),
            "diet_advice": list(result.diet_advice),
            "exercise_advice": list(result.exercise_advice),
            "warning_signs": list(result.warning_signs),
            "emergency_instructions": list(result.emergency_instructions),
            "follow_up_plan": list(result.follow_up_plan),
            "patient_checklist": list(result.patient_checklist),
            "confidence_score": result.confidence_score,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_markdown(self, result: PatientEducationResult) -> str:
        sections = [f"## Patient Summary\n\n{result.patient_summary}"]
        if result.diagnosis_explanation.strip():
            sections.append(f"## Diagnosis Explanation\n\n{result.diagnosis_explanation}")
        if result.medication_instructions:
            sections.append(
                "## Medication Instructions\n\n"
                + "\n".join(f"- {item}" for item in result.medication_instructions)
            )
        if result.home_care_plan:
            sections.append(
                "## Home Care Plan\n\n" + "\n".join(f"- {item}" for item in result.home_care_plan)
            )
        if result.lifestyle_advice:
            sections.append(
                "## Lifestyle Advice\n\n"
                + "\n".join(f"- {item}" for item in result.lifestyle_advice)
            )
        if result.diet_advice:
            sections.append(
                "## Diet Advice\n\n" + "\n".join(f"- {item}" for item in result.diet_advice)
            )
        if result.exercise_advice:
            sections.append(
                "## Exercise Advice\n\n" + "\n".join(f"- {item}" for item in result.exercise_advice)
            )
        if result.warning_signs:
            sections.append(
                "## Warning Signs\n\n" + "\n".join(f"- {item}" for item in result.warning_signs)
            )
        if result.emergency_instructions:
            sections.append(
                "## Emergency Instructions\n\n"
                + "\n".join(f"- {item}" for item in result.emergency_instructions)
            )
        if result.follow_up_plan:
            sections.append(
                "## Follow-up Plan\n\n" + "\n".join(f"- {item}" for item in result.follow_up_plan)
            )
        if result.patient_checklist:
            sections.append(
                "## Patient Checklist\n\n"
                + "\n".join(f"- {item}" for item in result.patient_checklist)
            )
        sections.append(
            f"## Confidence Score\n\n{self._format_confidence(result.confidence_score)}"
        )
        return "\n\n".join(sections)

    def _render_text(self, result: PatientEducationResult) -> str:
        sections = [f"PATIENT SUMMARY:\n{result.patient_summary}"]
        if result.diagnosis_explanation.strip():
            sections.append(f"DIAGNOSIS EXPLANATION:\n{result.diagnosis_explanation}")
        if result.medication_instructions:
            sections.append(
                "MEDICATION INSTRUCTIONS:\n"
                + "\n".join(f"- {item}" for item in result.medication_instructions)
            )
        if result.home_care_plan:
            sections.append(
                "HOME CARE PLAN:\n" + "\n".join(f"- {item}" for item in result.home_care_plan)
            )
        if result.lifestyle_advice:
            sections.append(
                "LIFESTYLE ADVICE:\n" + "\n".join(f"- {item}" for item in result.lifestyle_advice)
            )
        if result.diet_advice:
            sections.append(
                "DIET ADVICE:\n" + "\n".join(f"- {item}" for item in result.diet_advice)
            )
        if result.exercise_advice:
            sections.append(
                "EXERCISE ADVICE:\n" + "\n".join(f"- {item}" for item in result.exercise_advice)
            )
        if result.warning_signs:
            sections.append(
                "WARNING SIGNS:\n" + "\n".join(f"- {item}" for item in result.warning_signs)
            )
        if result.emergency_instructions:
            sections.append(
                "EMERGENCY INSTRUCTIONS:\n"
                + "\n".join(f"- {item}" for item in result.emergency_instructions)
            )
        if result.follow_up_plan:
            sections.append(
                "FOLLOW-UP PLAN:\n" + "\n".join(f"- {item}" for item in result.follow_up_plan)
            )
        if result.patient_checklist:
            sections.append(
                "PATIENT CHECKLIST:\n" + "\n".join(f"- {item}" for item in result.patient_checklist)
            )
        sections.append(f"CONFIDENCE SCORE:\n{self._format_confidence(result.confidence_score)}")
        return "\n\n".join(sections)

    def _format_confidence(self, confidence: float | None) -> str:
        return "Not provided." if confidence is None else f"{confidence:.2f}"
