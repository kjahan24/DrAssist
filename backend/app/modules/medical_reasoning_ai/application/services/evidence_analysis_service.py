"""`EvidenceAnalysisService` — the "evidence aggregation, evidence
weighting, conflicting evidence detection, red flag prioritization, risk
scoring, missing-information analysis" half of this task's own "REASONING
ENGINE" section. See `app.modules.medical_reasoning_ai.application.ports
.EvidenceAnalyzerPort`'s own docstring for the full split between what
this service computes itself (pure, no port) and what it delegates to
that port (deterministic but knowledge-dependent).

Lives in `application/services/`, not `infrastructure/`, the same
placement `app.modules.differential_diagnosis_ai.application.services
.clinical_reasoning_service.ClinicalReasoningService` uses for itself:
an application-layer service depending on its own module's port,
constructor-injected.

- "Evidence aggregation" is the parser's job (raw AI text -> one
  `tuple[EvidenceItem, ...]`) — this service operates on the already-
  aggregated collection.
- "Conflicting evidence detection" (`find_duplicates`) is pure, no port
  needed: the same normalized `EvidenceItem.description` appearing more
  than once — regardless of whether both occurrences share a polarity or
  span both `EvidencePolarity` values — is evidence the model
  duplicated/contradicted itself in wording, not a legitimate "argued on
  both sides" case (a legitimately debated topic gets *worded
  differently* on each side, e.g. "elevated troponin" (supporting) vs.
  "no ECG changes" (contradicting) — never the identical sentence twice).
  `infrastructure/validation/medical_reasoning_validator.py` calls this
  method directly rather than re-implementing the same check, per this
  task's own "Do NOT duplicate implementations" rule.
- "Evidence weighting" (`weight_evidence`) delegates per-item to
  `EvidenceAnalyzerPort.weight_evidence_item`.
- "Missing-information analysis" (`assess_missing_information`)
  delegates to `EvidenceAnalyzerPort.identify_missing_information`.
- "Risk scoring" and "red flag prioritization" (`prioritize_red_flags`)
  are combined: `EvidenceAnalyzerPort.compute_risk_score` is used to
  decide whether to escalate any non-`CRITICAL` red flag one priority
  level, then the (possibly escalated) flags are sorted by priority,
  most severe first.
"""

from dataclasses import replace

from app.modules.medical_reasoning_ai.application.ports import EvidenceAnalyzerPort
from app.modules.medical_reasoning_ai.domain.enums import RedFlagPriority
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    MedicalReasoningInput,
    RedFlag,
)

_PRIORITY_RANK: dict[RedFlagPriority, int] = {
    RedFlagPriority.LOW: 0,
    RedFlagPriority.MODERATE: 1,
    RedFlagPriority.HIGH: 2,
    RedFlagPriority.CRITICAL: 3,
}
_PRIORITY_BY_RANK: tuple[RedFlagPriority, ...] = (
    RedFlagPriority.LOW,
    RedFlagPriority.MODERATE,
    RedFlagPriority.HIGH,
    RedFlagPriority.CRITICAL,
)
_HIGH_RISK_ESCALATION_THRESHOLD = 0.6


class EvidenceAnalysisService:
    def __init__(self, *, analyzer: EvidenceAnalyzerPort) -> None:
        self._analyzer = analyzer

    def find_duplicates(self, items: tuple[EvidenceItem, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for item in items:
            normalized = item.description.strip().lower()
            if not normalized:
                continue
            if normalized in seen and item.description not in duplicates:
                duplicates.append(item.description)
            seen.add(normalized)
        return tuple(duplicates)

    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        return tuple(self._analyzer.weight_evidence_item(item) for item in items)

    def assess_missing_information(self, evidence: MedicalReasoningInput) -> tuple[str, ...]:
        return self._analyzer.identify_missing_information(evidence)

    def prioritize_red_flags(
        self, *, risk_factors: tuple[str, ...], red_flags: tuple[RedFlag, ...]
    ) -> tuple[RedFlag, ...]:
        if not red_flags:
            return ()
        risk_score = self._analyzer.compute_risk_score(
            risk_factors=risk_factors, red_flags=red_flags
        )
        escalated = tuple(self._maybe_escalate(flag, risk_score) for flag in red_flags)
        return tuple(
            sorted(escalated, key=lambda flag: _PRIORITY_RANK[flag.priority], reverse=True)
        )

    def _maybe_escalate(self, flag: RedFlag, risk_score: float) -> RedFlag:
        if risk_score < _HIGH_RISK_ESCALATION_THRESHOLD:
            return flag
        current_rank = _PRIORITY_RANK[flag.priority]
        if current_rank >= _PRIORITY_RANK[RedFlagPriority.CRITICAL]:
            return flag
        return replace(flag, priority=_PRIORITY_BY_RANK[current_rank + 1])
