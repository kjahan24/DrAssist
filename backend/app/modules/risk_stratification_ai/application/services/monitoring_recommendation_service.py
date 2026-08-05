"""`MonitoringRecommendationService` — this task's own explicitly-named
APPLICATION service, covering three related OUTPUT fields all driven by
which `RiskCategory` members ended up present in the merged
`risk_scores` collection:

- `recommend_monitoring` — this task's own "Recommended Monitoring"
  field: a curated, per-category monitoring-focus sentence, the same
  "each module defines its own local, necessarily-incomplete copy"
  precedent every prior AI module's own curated reference table
  establishes for itself.
- `suggest_follow_up` — this task's own "Suggested Follow-up" field:
  a curated, per-category follow-up sentence from the same table shape.
- `suggest_escalation` — this task's own "Suggested Escalation" field:
  delegates to `EarlyWarningPort.classify_escalation_urgency` per score
  rather than a static table, since escalation urgency depends on the
  score's own numeric value, not just its category (a `NEWS2` of 1 and a
  `NEWS2` of 9 warrant very different escalation language).
"""

from app.modules.risk_stratification_ai.application.ports import EarlyWarningPort
from app.modules.risk_stratification_ai.application.services._dedupe import (
    dedupe_preserving_order,
)
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import RiskScore

_MONITORING_BY_CATEGORY: dict[RiskCategory, str] = {
    RiskCategory.NEWS2: (
        "Continue routine NEWS2-based vital sign monitoring per local escalation protocol."
    ),
    RiskCategory.MEWS: (
        "Continue routine MEWS-based vital sign monitoring per local escalation protocol."
    ),
    RiskCategory.QSOFA: (
        "Monitor for signs of sepsis; repeat qSOFA and consider lactate/blood cultures if "
        "any parameter is met."
    ),
    RiskCategory.SOFA_SIMPLIFIED: (
        "Monitor organ function trends (respiratory, cardiovascular, neurological, renal)."
    ),
    RiskCategory.SEPSIS_RISK: (
        "Monitor temperature, heart rate, blood pressure, and mental status for signs of "
        "sepsis progression."
    ),
    RiskCategory.AKI_RISK: "Monitor urine output and serial serum creatinine.",
    RiskCategory.RESPIRATORY_DETERIORATION: (
        "Monitor respiratory rate, oxygen saturation, and work of breathing."
    ),
    RiskCategory.CARDIOVASCULAR_RISK: (
        "Monitor blood pressure, heart rate, and cardiac telemetry as indicated."
    ),
    RiskCategory.STROKE_RISK: "Monitor neurological status and blood pressure closely.",
    RiskCategory.BLEEDING_RISK: (
        "Monitor for overt or occult bleeding and hemoglobin/hematocrit trends."
    ),
    RiskCategory.FALL_RISK: "Implement fall-precaution monitoring and mobility assistance.",
    RiskCategory.READMISSION_RISK: (
        "Monitor for early signs of clinical decline prior to discharge."
    ),
    RiskCategory.MORTALITY_RISK: (
        "Monitor closely for clinical deterioration; consider a goals-of-care discussion."
    ),
    RiskCategory.GENERAL_CLINICAL_DETERIORATION: (
        "Continue frequent general clinical observation."
    ),
}

_FOLLOW_UP_BY_CATEGORY: dict[RiskCategory, str] = {
    RiskCategory.NEWS2: (
        "Reassess vital signs per NEWS2 monitoring frequency; escalate to the responsible "
        "clinician if the score increases."
    ),
    RiskCategory.MEWS: (
        "Reassess vital signs per MEWS monitoring frequency; escalate if the score increases."
    ),
    RiskCategory.QSOFA: (
        "Reassess for sepsis criteria and consider critical care referral if qSOFA remains "
        "elevated."
    ),
    RiskCategory.SOFA_SIMPLIFIED: (
        "Trend simplified SOFA components serially; escalate to critical care if deteriorating."
    ),
    RiskCategory.SEPSIS_RISK: (
        "Consider sepsis bundle initiation and infectious disease follow-up if risk factors "
        "persist."
    ),
    RiskCategory.AKI_RISK: "Arrange nephrology follow-up if renal function continues to decline.",
    RiskCategory.RESPIRATORY_DETERIORATION: (
        "Arrange pulmonology follow-up or repeat chest imaging if respiratory status worsens."
    ),
    RiskCategory.CARDIOVASCULAR_RISK: "Arrange cardiology follow-up for risk factor management.",
    RiskCategory.STROKE_RISK: (
        "Arrange neurology follow-up and consider a stroke risk-reduction workup."
    ),
    RiskCategory.BLEEDING_RISK: (
        "Reassess anticoagulant/antiplatelet therapy with the prescriber."
    ),
    RiskCategory.FALL_RISK: "Arrange a physical therapy assessment for gait and balance.",
    RiskCategory.READMISSION_RISK: (
        "Arrange early post-discharge follow-up and care coordination."
    ),
    RiskCategory.MORTALITY_RISK: (
        "Arrange multidisciplinary follow-up, including palliative care consultation if "
        "appropriate."
    ),
    RiskCategory.GENERAL_CLINICAL_DETERIORATION: (
        "Reassess the clinical trajectory and escalate per local deterioration protocol."
    ),
}


class MonitoringRecommendationService:
    def __init__(self, *, early_warning_port: EarlyWarningPort) -> None:
        self._early_warning_port = early_warning_port

    def recommend_monitoring(self, risk_scores: tuple[RiskScore, ...]) -> tuple[str, ...]:
        texts = tuple(
            _MONITORING_BY_CATEGORY[score.category]
            for score in risk_scores
            if score.category in _MONITORING_BY_CATEGORY
        )
        return dedupe_preserving_order(texts)

    def suggest_follow_up(self, risk_scores: tuple[RiskScore, ...]) -> tuple[str, ...]:
        texts = tuple(
            _FOLLOW_UP_BY_CATEGORY[score.category]
            for score in risk_scores
            if score.category in _FOLLOW_UP_BY_CATEGORY
        )
        return dedupe_preserving_order(texts)

    def suggest_escalation(self, risk_scores: tuple[RiskScore, ...]) -> tuple[str, ...]:
        texts: list[str] = []
        for score in risk_scores:
            urgency = self._early_warning_port.classify_escalation_urgency(score)
            if urgency is not None:
                texts.append(urgency)
        return dedupe_preserving_order(tuple(texts))
