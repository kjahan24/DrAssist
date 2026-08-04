"""`ClinicalReasoningService` — the deterministic half of this task's own
"CLINICAL REASONING" requirement. See
`app.modules.differential_diagnosis_ai.application.ports
.ClinicalReasoningPort`'s own docstring for the full split between
deterministic and AI-semantic reasoning categories.

Two independent responsibilities, each delegating to
`ClinicalReasoningPort`:

1. `upgrade_urgency_levels` — for each candidate, if the AI reported red-
   flag indicators but under-triaged the urgency level below the
   deterministic minimum `ClinicalReasoningPort.classify_minimum_urgency`
   computes for those flags, the urgency level is upgraded (never
   downgraded — this is a safety floor, not a ceiling). Used by
   `GenerateDifferentialDiagnosisUseCase` as a pipeline enrichment step,
   after validation succeeds, the same "validate the AI's own output
   first, then safety-enrich afterward" ordering
   `app.modules.prescription_ai.application.use_cases
   .generate_prescription_suggestion.GeneratePrescriptionSuggestionUseCase`
   uses for its own medication-safety enrichment.
2. `assess_missing_information` — delegates directly to
   `ClinicalReasoningPort.identify_missing_information`, used by
   `ValidateClinicalEvidenceUseCase` as part of its advisory pre-flight
   warnings.
"""

from dataclasses import replace

from app.modules.differential_diagnosis_ai.application.ports import ClinicalReasoningPort
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisInput,
)

_URGENCY_SEVERITY_ORDER = ("routine", "urgent", "emergent")


class ClinicalReasoningService:
    def __init__(self, *, reasoning: ClinicalReasoningPort) -> None:
        self._reasoning = reasoning

    def upgrade_urgency_levels(
        self, candidates: tuple[DifferentialDiagnosisCandidate, ...]
    ) -> tuple[DifferentialDiagnosisCandidate, ...]:
        return tuple(self._upgrade_one(candidate) for candidate in candidates)

    def _upgrade_one(
        self, candidate: DifferentialDiagnosisCandidate
    ) -> DifferentialDiagnosisCandidate:
        minimum_urgency = self._reasoning.classify_minimum_urgency(
            red_flag_indicators=candidate.red_flag_indicators,
            confidence_score=candidate.confidence_score,
        )
        current_rank = _URGENCY_SEVERITY_ORDER.index(candidate.urgency_level.value)
        minimum_rank = _URGENCY_SEVERITY_ORDER.index(minimum_urgency.value)
        if minimum_rank <= current_rank:
            return candidate
        return replace(candidate, urgency_level=minimum_urgency)

    def assess_missing_information(self, evidence: DifferentialDiagnosisInput) -> tuple[str, ...]:
        return self._reasoning.identify_missing_information(evidence)
