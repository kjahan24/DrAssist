"""`ICD10RankingService` — orders an already-generated, already-validated
`ICD10SuggestionSet` per this task's own "RANKING — Rank diagnoses using:
confidence, supporting evidence, clinical relevance" requirement.

Lives in `application/services/`, not `infrastructure/`, the same
placement `app.modules.soap_note_ai.application.services
.soap_note_renderer.SOAPNoteRenderer` uses for itself: no I/O of its own.
It does depend on `ICD10KnowledgePort` (an application-layer port, so an
application-layer service is allowed to depend on it) for the "clinical
relevance" signal — unlike `SOAPNoteRenderer`, ranking genuinely needs
that one collaborator, so it is constructor-injected rather than
imported directly.

Ordering, most to least important:

1. `flag` — a suggestion flagged `PRIMARY` always outranks every
   `SECONDARY` suggestion, regardless of the weighted score below. A
   primary/secondary flag is a stronger, more deliberate clinical signal
   than small differences in the weighted components, so it is not
   folded into the weighted average — it is a dominant sort key.
2. A weighted score combining:
   - confidence (60%) — the AI's own self-reported certainty;
   - clinical relevance (25%) — `ICD10KnowledgePort.lookup_canonical_name`
     resolving to a recognized common code is treated as full relevance
     credit; not resolving is *not* treated as irrelevant (the curated
     reference set is deliberately incomplete — see that port's own
     docstring), so it earns partial, not zero, credit;
   - supporting evidence presence (15%) — a suggestion with non-blank
     `supporting_evidence` outranks an otherwise-identical one without
     it.

`GenerateICD10SuggestionsUseCase` uses this service directly (not via
`RankICD10SuggestionsUseCase`) as the last pipeline step before
returning; `RankICD10SuggestionsUseCase` wraps the same service for a
caller that already has an assembled `ICD10SuggestionSet` from elsewhere
(e.g. merged across multiple generations) and wants it (re-)ranked
without a further AI call.
"""

from app.modules.icd10_ai.application.ports import ICD10KnowledgePort
from app.modules.icd10_ai.domain.enums import DiagnosisFlag
from app.modules.icd10_ai.domain.value_objects import ICD10Suggestion, ICD10SuggestionSet

_CONFIDENCE_WEIGHT = 0.60
_RELEVANCE_WEIGHT = 0.25
_EVIDENCE_WEIGHT = 0.15
_KNOWN_CODE_RELEVANCE = 1.0
_UNKNOWN_CODE_RELEVANCE = 0.5


class ICD10RankingService:
    def __init__(self, *, knowledge: ICD10KnowledgePort) -> None:
        self._knowledge = knowledge

    def rank(self, suggestion_set: ICD10SuggestionSet) -> ICD10SuggestionSet:
        ranked = sorted(suggestion_set.suggestions, key=self._sort_key, reverse=True)
        return ICD10SuggestionSet(
            suggestions=tuple(ranked),
            raw_text=suggestion_set.raw_text,
            output_format=suggestion_set.output_format,
        )

    def _sort_key(self, suggestion: ICD10Suggestion) -> tuple[bool, float]:
        is_primary = suggestion.flag is DiagnosisFlag.PRIMARY
        return (is_primary, self._weighted_score(suggestion))

    def _weighted_score(self, suggestion: ICD10Suggestion) -> float:
        confidence = suggestion.confidence_score or 0.0
        relevance = (
            _KNOWN_CODE_RELEVANCE
            if self._knowledge.lookup_canonical_name(suggestion.icd10_code) is not None
            else _UNKNOWN_CODE_RELEVANCE
        )
        evidence = 1.0 if suggestion.supporting_evidence.strip() else 0.0
        return (
            (_CONFIDENCE_WEIGHT * confidence)
            + (_RELEVANCE_WEIGHT * relevance)
            + (_EVIDENCE_WEIGHT * evidence)
        )
