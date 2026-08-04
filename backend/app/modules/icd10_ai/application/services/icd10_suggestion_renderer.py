"""`ICD10SuggestionRenderer` — pure, I/O-free formatting from a structured
`ICD10SuggestionSet` into one of this task's three output shapes (JSON,
Markdown, plain text). Lives in `application/services/`, not
`infrastructure/`, the same placement
`app.modules.soap_note_ai.application.services.soap_note_renderer
.SOAPNoteRenderer` uses for itself: no external port dependency, no I/O,
just a plain concrete service.

No use case wraps this renderer — unlike
`app.modules.soap_note_ai.application.use_cases.render_soap_note
.RenderSOAPNoteUseCase`, this task's own APPLICATION section names
exactly three use cases (`GenerateICD10SuggestionsUseCase`,
`ValidateClinicalContextUseCase`, `RankICD10SuggestionsUseCase`) and
omits a rendering one, so `public/facade.py::ICD10AIFacade.render_suggestions`
calls this service directly — a use-case wrapper here would add no logic
beyond a single delegating call.
"""

import json

from app.modules.icd10_ai.domain.enums import ICD10OutputFormat
from app.modules.icd10_ai.domain.value_objects import ICD10Suggestion, ICD10SuggestionSet


class ICD10SuggestionRenderer:
    def render(self, suggestion_set: ICD10SuggestionSet, target_format: ICD10OutputFormat) -> str:
        if target_format is ICD10OutputFormat.JSON:
            return self._render_json(suggestion_set)
        if target_format is ICD10OutputFormat.MARKDOWN:
            return self._render_markdown(suggestion_set)
        return self._render_text(suggestion_set)

    def _render_json(self, suggestion_set: ICD10SuggestionSet) -> str:
        payload = {
            "suggestions": [
                {
                    "icd10_code": s.icd10_code,
                    "diagnosis_name": s.diagnosis_name,
                    "confidence_score": s.confidence_score,
                    "clinical_reasoning": s.clinical_reasoning,
                    "supporting_evidence": s.supporting_evidence,
                    "flag": s.flag.value,
                }
                for s in suggestion_set.suggestions
            ]
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _render_markdown(self, suggestion_set: ICD10SuggestionSet) -> str:
        return "\n\n".join(self._render_markdown_block(s) for s in suggestion_set.suggestions)

    def _render_markdown_block(self, suggestion: ICD10Suggestion) -> str:
        return (
            f"## {suggestion.icd10_code} — {suggestion.diagnosis_name} "
            f"({suggestion.flag.value})\n\n"
            f"**Confidence:** {self._format_confidence(suggestion.confidence_score)}\n\n"
            f"**Clinical Reasoning:** {suggestion.clinical_reasoning}\n\n"
            f"**Supporting Evidence:** {suggestion.supporting_evidence}"
        )

    def _render_text(self, suggestion_set: ICD10SuggestionSet) -> str:
        return "\n\n".join(self._render_text_block(s) for s in suggestion_set.suggestions)

    def _render_text_block(self, suggestion: ICD10Suggestion) -> str:
        return (
            f"{suggestion.icd10_code} - {suggestion.diagnosis_name} "
            f"[{suggestion.flag.value.upper()}]\n"
            f"CONFIDENCE: {self._format_confidence(suggestion.confidence_score)}\n"
            f"CLINICAL REASONING: {suggestion.clinical_reasoning}\n"
            f"SUPPORTING EVIDENCE: {suggestion.supporting_evidence}"
        )

    def _format_confidence(self, confidence_score: float | None) -> str:
        return "Not provided." if confidence_score is None else f"{confidence_score:.2f}"
