"""`RiskScoringService` — this task's own explicitly-named APPLICATION
service, the thin orchestration layer over `RiskScoringPort` that
computes every standardized clinical score this task's own ASSESS
section names (NEWS2, MEWS, qSOFA, SOFA (simplified)) from one
`VitalSigns` (+ `lab_values` for the SOFA-simplified renal component),
dropping whichever scores `RiskScoringPort` itself could not compute
from the given data (see that port's own docstring for why each method
returns `None` rather than a fabricated partial score).
"""

from app.modules.risk_stratification_ai.application.ports import RiskScoringPort
from app.modules.risk_stratification_ai.domain.value_objects import (
    LabValue,
    RiskScore,
    VitalSigns,
)


class RiskScoringService:
    def __init__(self, *, scoring_port: RiskScoringPort) -> None:
        self._scoring_port = scoring_port

    def compute_standardized_scores(
        self, vital_signs: VitalSigns, lab_values: tuple[LabValue, ...]
    ) -> tuple[RiskScore, ...]:
        candidates = (
            self._scoring_port.compute_news2(vital_signs),
            self._scoring_port.compute_mews(vital_signs),
            self._scoring_port.compute_qsofa(vital_signs),
            self._scoring_port.compute_sofa_simplified(vital_signs, lab_values),
        )
        return tuple(score for score in candidates if score is not None)
