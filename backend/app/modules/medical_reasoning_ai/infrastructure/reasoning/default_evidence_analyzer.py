"""`DefaultEvidenceAnalyzer` — the one concrete `EvidenceAnalyzerPort`
implementation this task ships. See that port's own docstring
(`application/ports.py`) for the full split between what it computes and
why each capability is deterministic-but-knowledge-dependent enough to
warrant a port instead of living directly on
`application/services/evidence_analysis_service.EvidenceAnalysisService`.

`_OBJECTIVE_KEYWORDS` is a small curated set of measurable/objective-data
markers (units, lab/vital abbreviations) — a real production system might
instead consult a structured clinical-terminology/UMLS-style knowledge
base here; this module's own small, rule-based implementation is the
pragmatic in-repo substitute, the same "each module defines its own
local, necessarily-incomplete copy" precedent
`app.modules.differential_diagnosis_ai.infrastructure.reasoning
.clinical_reasoning_advisor.DefaultClinicalReasoningAdvisor` already
establishes for its own module.

`compute_risk_score` weights each `RedFlagPriority` and adds a smaller
per-risk-factor contribution — see `application/services
.evidence_analysis_service.EvidenceAnalysisService.prioritize_red_flags`
for how the resulting score drives red-flag escalation.
"""

from dataclasses import replace

from app.modules.medical_reasoning_ai.application.ports import EvidenceAnalyzerPort
from app.modules.medical_reasoning_ai.domain.enums import RedFlagPriority
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    MedicalReasoningInput,
    RedFlag,
)

_OBJECTIVE_KEYWORDS = (
    "mg",
    "mmhg",
    "bpm",
    "mmol",
    "wbc",
    "hgb",
    "creatinine",
    "troponin",
    "°c",
    "°f",
    "spo2",
    "hr:",
    "bp:",
)
_OBJECTIVE_WEIGHT_BOOST = 0.15
_MAX_WEIGHT = 1.0

_RISK_FACTOR_CONTRIBUTION = 0.10
_RED_FLAG_PRIORITY_CONTRIBUTION: dict[RedFlagPriority, float] = {
    RedFlagPriority.LOW: 0.10,
    RedFlagPriority.MODERATE: 0.20,
    RedFlagPriority.HIGH: 0.30,
    RedFlagPriority.CRITICAL: 0.45,
}


class DefaultEvidenceAnalyzer(EvidenceAnalyzerPort):
    def weight_evidence_item(self, item: EvidenceItem) -> EvidenceItem:
        description_lower = item.description.lower()
        if any(keyword in description_lower for keyword in _OBJECTIVE_KEYWORDS):
            return replace(item, weight=min(_MAX_WEIGHT, item.weight + _OBJECTIVE_WEIGHT_BOOST))
        return item

    def identify_missing_information(self, evidence: MedicalReasoningInput) -> tuple[str, ...]:
        missing: list[str] = []

        has_narrative_content = bool(
            (evidence.history_of_present_illness or "").strip()
            or evidence.symptoms
            or (evidence.review_of_systems or "").strip()
        )
        if not has_narrative_content:
            missing.append(
                "no HPI, symptoms, or review of systems provided — reasoning quality "
                "depends heavily on the presenting narrative"
            )

        has_objective_content = bool(
            (evidence.physical_examination or "").strip() or evidence.vitals
        )
        if not has_objective_content:
            missing.append("no physical examination findings or vitals provided")

        if not evidence.laboratory_results and not (evidence.imaging_summary or "").strip():
            missing.append("no laboratory results or imaging summary provided")

        if not evidence.allergies and not evidence.medications:
            missing.append("no allergy or medication information provided")

        return tuple(missing)

    def compute_risk_score(
        self, *, risk_factors: tuple[str, ...], red_flags: tuple[RedFlag, ...]
    ) -> float:
        flag_contribution = sum(
            _RED_FLAG_PRIORITY_CONTRIBUTION[flag.priority] for flag in red_flags
        )
        risk_factor_contribution = _RISK_FACTOR_CONTRIBUTION * len(risk_factors)
        return min(1.0, flag_contribution + risk_factor_contribution)
