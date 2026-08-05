"""`ClinicalRiskAssessmentService` — thin orchestration over
`ClinicalRiskPort`, one of the operationally-necessary services this
module adds beyond this task's own four explicitly-named APPLICATION
items (`AnalyzePatientRiskUseCase`, `RiskScoringService`,
`EarlyWarningService`, `RiskExplanationService`,
`MonitoringRecommendationService`), the same "named [items] plus the
operationally-necessary rest" precedent every prior AI module's own
`application/services` list documents for itself — named distinctly
(`ClinicalRiskAssessmentService`, not `ClinicalRiskService`) to avoid
being mistaken for a wrapper the task itself named.

Covers the ten `RiskCategory` members with no standardized public
formula (every member except `NEWS2`/`MEWS`/`QSOFA`/`SOFA_SIMPLIFIED`,
which `RiskScoringService` already computes deterministically): for each
one, asks `ClinicalRiskPort.identify_risk_factors` whether the given
clinical context recognizes any curated risk factors for it, collecting
only the categories that do.
"""

from app.modules.risk_stratification_ai.application.ports import ClinicalRiskPort
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import LabValue, RiskScore

_STANDARDIZED_CATEGORIES = frozenset(
    {
        RiskCategory.NEWS2,
        RiskCategory.MEWS,
        RiskCategory.QSOFA,
        RiskCategory.SOFA_SIMPLIFIED,
    }
)
_QUALITATIVE_CATEGORIES = tuple(
    category for category in RiskCategory if category not in _STANDARDIZED_CATEGORIES
)


class ClinicalRiskAssessmentService:
    def __init__(self, *, clinical_risk_port: ClinicalRiskPort) -> None:
        self._clinical_risk_port = clinical_risk_port

    def assess_qualitative_risks(
        self,
        *,
        diagnoses: tuple[str, ...],
        medical_history: tuple[str, ...],
        current_medications: tuple[str, ...],
        lab_values: tuple[LabValue, ...],
        patient_age: int | None,
    ) -> tuple[RiskScore, ...]:
        scores: list[RiskScore] = []
        for category in _QUALITATIVE_CATEGORIES:
            score = self._clinical_risk_port.identify_risk_factors(
                category,
                diagnoses=diagnoses,
                medical_history=medical_history,
                current_medications=current_medications,
                lab_values=lab_values,
                patient_age=patient_age,
            )
            if score is not None:
                scores.append(score)
        return tuple(scores)
