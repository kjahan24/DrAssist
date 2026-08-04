"""`PrescriptionSuggestionRenderer` — pure, I/O-free formatting from a
structured `PrescriptionSuggestionSet` into one of this task's three
output shapes (JSON, Markdown, plain text). Lives in
`application/services/`, not `infrastructure/`, the same placement
`app.modules.icd10_ai.application.services.icd10_suggestion_renderer
.ICD10SuggestionRenderer` uses for itself: no external port dependency,
no I/O, just a plain concrete service.

No use case wraps this renderer — unlike
`app.modules.soap_note_ai.application.use_cases.render_soap_note
.RenderSOAPNoteUseCase`, this task's own APPLICATION section names
exactly three use cases (`GeneratePrescriptionSuggestionUseCase`,
`ValidatePrescriptionContextUseCase`, `AnalyzeMedicationSafetyUseCase`)
and omits a rendering one, so `public/facade.py
::PrescriptionAIFacade.render_suggestions` calls this service directly —
a use-case wrapper here would add no logic beyond a single delegating
call, the same choice `app.modules.icd10_ai.public.facade.ICD10AIFacade`
makes for its own renderer.
"""

import json

from app.modules.prescription_ai.domain.enums import PrescriptionOutputFormat
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSafetyFinding,
    MedicationSuggestion,
    PrescriptionSuggestionSet,
)


class PrescriptionSuggestionRenderer:
    def render(
        self, suggestion_set: PrescriptionSuggestionSet, target_format: PrescriptionOutputFormat
    ) -> str:
        if target_format is PrescriptionOutputFormat.JSON:
            return self._render_json(suggestion_set)
        if target_format is PrescriptionOutputFormat.MARKDOWN:
            return self._render_markdown(suggestion_set)
        return self._render_text(suggestion_set)

    def _render_json(self, suggestion_set: PrescriptionSuggestionSet) -> str:
        payload = {
            "medications": [
                {
                    "generic_name": m.generic_name,
                    "brand_name": m.brand_name,
                    "strength": m.strength,
                    "dosage": m.dosage,
                    "route": m.route.value,
                    "frequency": m.frequency,
                    "duration": m.duration,
                    "quantity": m.quantity,
                    "is_prn": m.is_prn,
                    "clinical_indication": m.clinical_indication,
                    "monitoring_advice": m.monitoring_advice,
                    "patient_instructions": m.patient_instructions,
                    "confidence_score": m.confidence_score,
                    "clinical_reasoning": m.clinical_reasoning,
                }
                for m in suggestion_set.medications
            ],
            "safety_findings": [
                {
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "description": f.description,
                    "affected_medications": list(f.affected_medications),
                }
                for f in suggestion_set.safety_findings
            ],
            "monitoring_recommendations": list(suggestion_set.monitoring_recommendations),
            "follow_up_recommendations": list(suggestion_set.follow_up_recommendations),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_markdown(self, suggestion_set: PrescriptionSuggestionSet) -> str:
        sections = [self._render_markdown_medication(m) for m in suggestion_set.medications]
        if suggestion_set.safety_findings:
            sections.append(
                "## Safety Findings\n\n"
                + "\n\n".join(
                    self._render_markdown_finding(f) for f in suggestion_set.safety_findings
                )
            )
        if suggestion_set.monitoring_recommendations:
            sections.append(
                "## Monitoring Recommendations\n\n"
                + "\n".join(f"- {r}" for r in suggestion_set.monitoring_recommendations)
            )
        if suggestion_set.follow_up_recommendations:
            sections.append(
                "## Follow-up Recommendations\n\n"
                + "\n".join(f"- {r}" for r in suggestion_set.follow_up_recommendations)
            )
        return "\n\n".join(sections)

    def _render_markdown_medication(self, medication: MedicationSuggestion) -> str:
        brand = f" ({medication.brand_name})" if medication.brand_name else ""
        prn = " — PRN" if medication.is_prn else ""
        return (
            f"## {medication.generic_name}{brand}{prn}\n\n"
            f"**Strength:** {medication.strength}\n\n"
            f"**Dosage:** {medication.dosage}\n\n"
            f"**Route:** {medication.route.value}\n\n"
            f"**Frequency:** {medication.frequency}\n\n"
            f"**Duration:** {medication.duration}\n\n"
            f"**Quantity:** {medication.quantity}\n\n"
            f"**Clinical Indication:** {medication.clinical_indication}\n\n"
            f"**Monitoring Advice:** {medication.monitoring_advice}\n\n"
            f"**Patient Instructions:** {medication.patient_instructions}\n\n"
            f"**Confidence:** {self._format_confidence(medication.confidence_score)}\n\n"
            f"**Clinical Reasoning:** {medication.clinical_reasoning}"
        )

    def _render_markdown_finding(self, finding: MedicationSafetyFinding) -> str:
        affected = ", ".join(finding.affected_medications) if finding.affected_medications else "—"
        return (
            f"- **{finding.category.value}** ({finding.severity.value}): {finding.description} "
            f"[{affected}]"
        )

    def _render_text(self, suggestion_set: PrescriptionSuggestionSet) -> str:
        sections = [self._render_text_medication(m) for m in suggestion_set.medications]
        if suggestion_set.safety_findings:
            sections.append(
                "SAFETY FINDINGS:\n"
                + "\n".join(self._render_text_finding(f) for f in suggestion_set.safety_findings)
            )
        if suggestion_set.monitoring_recommendations:
            sections.append(
                "MONITORING RECOMMENDATIONS:\n"
                + "\n".join(f"- {r}" for r in suggestion_set.monitoring_recommendations)
            )
        if suggestion_set.follow_up_recommendations:
            sections.append(
                "FOLLOW-UP RECOMMENDATIONS:\n"
                + "\n".join(f"- {r}" for r in suggestion_set.follow_up_recommendations)
            )
        return "\n\n".join(sections)

    def _render_text_medication(self, medication: MedicationSuggestion) -> str:
        prn = " [PRN]" if medication.is_prn else ""
        return (
            f"{medication.generic_name.upper()}{prn}\n"
            f"STRENGTH: {medication.strength}\n"
            f"DOSAGE: {medication.dosage}\n"
            f"ROUTE: {medication.route.value}\n"
            f"FREQUENCY: {medication.frequency}\n"
            f"DURATION: {medication.duration}\n"
            f"QUANTITY: {medication.quantity}\n"
            f"CLINICAL INDICATION: {medication.clinical_indication}\n"
            f"MONITORING ADVICE: {medication.monitoring_advice}\n"
            f"PATIENT INSTRUCTIONS: {medication.patient_instructions}\n"
            f"CONFIDENCE: {self._format_confidence(medication.confidence_score)}\n"
            f"CLINICAL REASONING: {medication.clinical_reasoning}"
        )

    def _render_text_finding(self, finding: MedicationSafetyFinding) -> str:
        affected = ", ".join(finding.affected_medications) if finding.affected_medications else "-"
        return (
            f"[{finding.severity.value.upper()}] {finding.category.value}: "
            f"{finding.description} ({affected})"
        )

    def _format_confidence(self, confidence_score: float | None) -> str:
        return "Not provided." if confidence_score is None else f"{confidence_score:.2f}"
