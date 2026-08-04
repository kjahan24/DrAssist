"""`DifferentialDiagnosisRankingService` — this task's own "confidence
ranking" clinical-reasoning requirement, applied as a pure re-ordering of
an already-generated, already-validated `DifferentialDiagnosisResult`.

Lives in `application/services/`, not `infrastructure/`, the same
placement `app.modules.icd10_ai.application.services
.icd10_ranking_service.ICD10RankingService` uses for itself: no I/O,
pure sort.

Primary key: `confidence_score` (missing/`None` treated as `0.0`,
descending). Secondary key (tie-break only): `urgency_level` severity —
among candidates the AI rated equally confident, the more acute one is
surfaced first, since urgency is itself part of what should drive
clinical attention. `DifferentialDiagnosisResult.most_likely_diagnosis`
is a computed property over `candidates[0]`, so ranking is the single
place that decides what "most likely" means — see that value object's
own docstring.

`GenerateDifferentialDiagnosisUseCase` uses this service directly (not
via `RankDifferentialDiagnosisUseCase`) as its own last pipeline step;
`RankDifferentialDiagnosisUseCase` wraps the same service for a caller
that already has an assembled `DifferentialDiagnosisResult` from
elsewhere and wants it (re-)ranked without a further AI call — the same
"standalone entry point onto a shared service" shape
`app.modules.icd10_ai.application.use_cases.rank_icd10_suggestions
.RankICD10SuggestionsUseCase` establishes for itself.
"""

from dataclasses import replace

from app.modules.differential_diagnosis_ai.domain.enums import UrgencyLevel
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisResult,
)

_URGENCY_SEVERITY: dict[UrgencyLevel, int] = {
    UrgencyLevel.ROUTINE: 0,
    UrgencyLevel.URGENT: 1,
    UrgencyLevel.EMERGENT: 2,
}


class DifferentialDiagnosisRankingService:
    def rank(self, result: DifferentialDiagnosisResult) -> DifferentialDiagnosisResult:
        ranked = sorted(result.candidates, key=self._sort_key, reverse=True)
        return replace(result, candidates=tuple(ranked))

    def _sort_key(self, candidate: DifferentialDiagnosisCandidate) -> tuple[float, int]:
        confidence = candidate.confidence_score or 0.0
        urgency_severity = _URGENCY_SEVERITY[candidate.urgency_level]
        return (confidence, urgency_severity)
