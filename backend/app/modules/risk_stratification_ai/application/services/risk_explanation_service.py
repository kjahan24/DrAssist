"""`RiskExplanationService` — this task's own explicitly-named
APPLICATION service, covering two related concerns:

- `merge_risk_scores` — reconciles the AI-reported `risk_scores` with
  `RiskScoringService`/`ClinicalRiskAssessmentService`'s own
  deterministically-computed scores, one `RiskScore` per `RiskCategory`:
  a deterministic score's own `score_value` always wins over an
  AI-reported one for the same category (deterministic data is more
  trustworthy than an unverified AI claim, the same "deterministic
  floor/override" precedent `application/services
  /early_warning_service.py` documents for itself), while
  `contributing_factors` from both sources are combined (deduplicated,
  order preserved) so no AI-surfaced factor is silently dropped, and
  `clinical_explanation` prefers whichever source actually wrote one.
- `build_clinical_reasoning` — this task's own top-level "Clinical
  Reasoning" OUTPUT field: returns the AI's own reasoning text unchanged
  when it wrote one, and otherwise synthesizes a minimal fallback from
  the merged risk scores' own `clinical_explanation` fields rather than
  leaving the field blank.
"""

from dataclasses import replace

from app.modules.risk_stratification_ai.application.services._dedupe import (
    dedupe_preserving_order,
)
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import RiskScore


class RiskExplanationService:
    def merge_risk_scores(
        self, ai_scores: tuple[RiskScore, ...], deterministic_scores: tuple[RiskScore, ...]
    ) -> tuple[RiskScore, ...]:
        merged: dict[RiskCategory, RiskScore] = {}
        for score in ai_scores:
            merged[score.category] = score
        for det_score in deterministic_scores:
            existing = merged.get(det_score.category)
            if existing is None:
                merged[det_score.category] = det_score
                continue
            merged[det_score.category] = replace(
                det_score,
                contributing_factors=dedupe_preserving_order(
                    existing.contributing_factors + det_score.contributing_factors
                ),
                clinical_explanation=(
                    existing.clinical_explanation.strip() or det_score.clinical_explanation
                ),
            )
        return tuple(merged.values())

    def build_clinical_reasoning(
        self, ai_reasoning: str, risk_scores: tuple[RiskScore, ...]
    ) -> str:
        if ai_reasoning.strip():
            return ai_reasoning
        explanations = [
            score.clinical_explanation
            for score in risk_scores
            if score.clinical_explanation.strip()
        ]
        return " ".join(explanations)
