"""`DifferentialDiagnosisRenderer` — pure, I/O-free formatting from a
structured `DifferentialDiagnosisResult` into one of this task's three
output shapes (JSON, Markdown, plain text). Lives in
`application/services/`, not `infrastructure/`, the same placement
`app.modules.prescription_ai.application.services
.prescription_suggestion_renderer.PrescriptionSuggestionRenderer` uses
for itself: no external port dependency, no I/O, just a plain concrete
service.

No use case wraps this renderer — unlike
`app.modules.soap_note_ai.application.use_cases.render_soap_note
.RenderSOAPNoteUseCase`, this task's own APPLICATION section names
exactly three use cases (`GenerateDifferentialDiagnosisUseCase`,
`RankDifferentialDiagnosisUseCase`, `ValidateClinicalEvidenceUseCase`)
and omits a rendering one, so `public/facade.py
::DifferentialDiagnosisAIFacade.render_result` calls this service
directly — the same choice
`app.modules.prescription_ai.public.facade.PrescriptionAIFacade` makes
for its own renderer.
"""

import json

from app.modules.differential_diagnosis_ai.domain.enums import DifferentialOutputFormat
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisResult,
)


class DifferentialDiagnosisRenderer:
    def render(
        self, result: DifferentialDiagnosisResult, target_format: DifferentialOutputFormat
    ) -> str:
        if target_format is DifferentialOutputFormat.JSON:
            return self._render_json(result)
        if target_format is DifferentialOutputFormat.MARKDOWN:
            return self._render_markdown(result)
        return self._render_text(result)

    def _render_json(self, result: DifferentialDiagnosisResult) -> str:
        payload = {
            "most_likely_diagnosis": result.most_likely_diagnosis,
            "candidates": [
                {
                    "disease_name": c.disease_name,
                    "icd10_code": c.icd10_code,
                    "confidence_score": c.confidence_score,
                    "clinical_reasoning": c.clinical_reasoning,
                    "supporting_findings": list(c.supporting_findings),
                    "findings_against": list(c.findings_against),
                    "recommended_next_tests": list(c.recommended_next_tests),
                    "red_flag_indicators": list(c.red_flag_indicators),
                    "urgency_level": c.urgency_level.value,
                }
                for c in result.candidates
            ],
            "serious_diagnoses_not_to_miss": list(result.serious_diagnoses_not_to_miss),
            "suggested_investigations": list(result.suggested_investigations),
            "suggested_referrals": list(result.suggested_referrals),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_markdown(self, result: DifferentialDiagnosisResult) -> str:
        sections = []
        if result.most_likely_diagnosis is not None:
            sections.append(f"## Most Likely Diagnosis\n\n{result.most_likely_diagnosis}")
        sections.extend(self._render_markdown_candidate(c) for c in result.candidates)
        if result.serious_diagnoses_not_to_miss:
            sections.append(
                "## Serious Diagnoses Not To Miss\n\n"
                + "\n".join(f"- {d}" for d in result.serious_diagnoses_not_to_miss)
            )
        if result.suggested_investigations:
            sections.append(
                "## Suggested Investigations\n\n"
                + "\n".join(f"- {i}" for i in result.suggested_investigations)
            )
        if result.suggested_referrals:
            sections.append(
                "## Suggested Referrals\n\n"
                + "\n".join(f"- {r}" for r in result.suggested_referrals)
            )
        return "\n\n".join(sections)

    def _render_markdown_candidate(self, candidate: DifferentialDiagnosisCandidate) -> str:
        icd10 = f" ({candidate.icd10_code})" if candidate.icd10_code else ""
        return (
            f"## {candidate.disease_name}{icd10}\n\n"
            f"**Confidence:** {self._format_confidence(candidate.confidence_score)}\n\n"
            f"**Urgency:** {candidate.urgency_level.value}\n\n"
            f"**Clinical Reasoning:** {candidate.clinical_reasoning}\n\n"
            f"**Supporting Findings:** {self._join(candidate.supporting_findings)}\n\n"
            f"**Findings Against:** {self._join(candidate.findings_against)}\n\n"
            f"**Recommended Next Tests:** {self._join(candidate.recommended_next_tests)}\n\n"
            f"**Red Flag Indicators:** {self._join(candidate.red_flag_indicators)}"
        )

    def _render_text(self, result: DifferentialDiagnosisResult) -> str:
        sections = []
        if result.most_likely_diagnosis is not None:
            sections.append(f"MOST LIKELY DIAGNOSIS: {result.most_likely_diagnosis}")
        sections.extend(self._render_text_candidate(c) for c in result.candidates)
        if result.serious_diagnoses_not_to_miss:
            sections.append(
                "SERIOUS DIAGNOSES NOT TO MISS:\n"
                + "\n".join(f"- {d}" for d in result.serious_diagnoses_not_to_miss)
            )
        if result.suggested_investigations:
            sections.append(
                "SUGGESTED INVESTIGATIONS:\n"
                + "\n".join(f"- {i}" for i in result.suggested_investigations)
            )
        if result.suggested_referrals:
            sections.append(
                "SUGGESTED REFERRALS:\n" + "\n".join(f"- {r}" for r in result.suggested_referrals)
            )
        return "\n\n".join(sections)

    def _render_text_candidate(self, candidate: DifferentialDiagnosisCandidate) -> str:
        icd10 = f" ({candidate.icd10_code})" if candidate.icd10_code else ""
        return (
            f"{candidate.disease_name.upper()}{icd10} [{candidate.urgency_level.value.upper()}]\n"
            f"CONFIDENCE: {self._format_confidence(candidate.confidence_score)}\n"
            f"CLINICAL REASONING: {candidate.clinical_reasoning}\n"
            f"SUPPORTING FINDINGS: {self._join(candidate.supporting_findings)}\n"
            f"FINDINGS AGAINST: {self._join(candidate.findings_against)}\n"
            f"RECOMMENDED NEXT TESTS: {self._join(candidate.recommended_next_tests)}\n"
            f"RED FLAG INDICATORS: {self._join(candidate.red_flag_indicators)}"
        )

    def _join(self, items: tuple[str, ...]) -> str:
        return ", ".join(items) if items else "None noted."

    def _format_confidence(self, confidence_score: float | None) -> str:
        return "Not provided." if confidence_score is None else f"{confidence_score:.2f}"
