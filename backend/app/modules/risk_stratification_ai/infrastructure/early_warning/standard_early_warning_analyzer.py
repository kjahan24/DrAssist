"""`StandardEarlyWarningAnalyzer` — the one concrete `EarlyWarningPort`
implementation this task ships.

`identify_single_parameter_triggers` reuses the same per-parameter NEWS2
point functions (`infrastructure/clinical_scoring/news2_parameters.py`)
`standard_risk_scoring_calculator.py` sums into the aggregate NEWS2
total, to surface exactly the parameters that scored the maximum 3
points on their own, per NEWS2's own official "any single parameter
scoring 3 triggers an urgent response" escalation rule, independent of
the aggregate total.

`classify_escalation_urgency` maps a computed `RiskScore` onto
escalation language using each standardized score's own well-known
clinical threshold bands; it returns `None` for the ten AI-assessed
categories (they carry no standardized numeric scale to threshold
against) and for a standardized score whose value indicates no
escalation is needed.
"""

from app.modules.risk_stratification_ai.application.ports import EarlyWarningPort
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import RiskScore, VitalSigns
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    consciousness_points,
    heart_rate_points,
    oxygen_saturation_points,
    respiratory_rate_points,
    systolic_bp_points,
    temperature_points,
)

_MAX_SINGLE_PARAMETER_POINTS = 3


def _news2_escalation(score_value: float) -> str | None:
    if score_value >= 7:
        return "Immediate escalation to critical care outreach/rapid response team (NEWS2 >= 7)."
    if score_value >= 5:
        return "Urgent clinician review required within 1 hour (NEWS2 5-6)."
    if score_value >= 1:
        return "Routine ward-based review; reassess per local monitoring protocol (NEWS2 1-4)."
    return None


def _mews_escalation(score_value: float) -> str | None:
    if score_value >= 5:
        return "Urgent clinician review required (MEWS >= 5)."
    if score_value >= 3:
        return "Increase observation frequency and consider clinician review (MEWS 3-4)."
    return None


def _qsofa_escalation(score_value: float) -> str | None:
    if score_value >= 2:
        return "Consider sepsis workup and escalate to a senior clinician (qSOFA >= 2)."
    return None


def _sofa_simplified_escalation(score_value: float) -> str | None:
    if score_value >= 5:
        return "Critical care escalation warranted (simplified SOFA >= 5)."
    if score_value >= 3:
        return (
            "Escalate to a senior clinician for organ dysfunction assessment "
            "(simplified SOFA 3-4)."
        )
    return None


_ESCALATION_FUNCTIONS = {
    RiskCategory.NEWS2: _news2_escalation,
    RiskCategory.MEWS: _mews_escalation,
    RiskCategory.QSOFA: _qsofa_escalation,
    RiskCategory.SOFA_SIMPLIFIED: _sofa_simplified_escalation,
}


class StandardEarlyWarningAnalyzer(EarlyWarningPort):
    def identify_single_parameter_triggers(self, vital_signs: VitalSigns) -> tuple[str, ...]:
        triggers: list[str] = []
        if vital_signs.respiratory_rate is not None:
            points, label = respiratory_rate_points(vital_signs.respiratory_rate)
            if points >= _MAX_SINGLE_PARAMETER_POINTS:
                triggers.append(f"Single-parameter trigger: {label}")
        if vital_signs.oxygen_saturation is not None:
            points, label = oxygen_saturation_points(vital_signs.oxygen_saturation)
            if points >= _MAX_SINGLE_PARAMETER_POINTS:
                triggers.append(f"Single-parameter trigger: {label}")
        if vital_signs.systolic_bp is not None:
            points, label = systolic_bp_points(vital_signs.systolic_bp)
            if points >= _MAX_SINGLE_PARAMETER_POINTS:
                triggers.append(f"Single-parameter trigger: {label}")
        if vital_signs.heart_rate is not None:
            points, label = heart_rate_points(vital_signs.heart_rate)
            if points >= _MAX_SINGLE_PARAMETER_POINTS:
                triggers.append(f"Single-parameter trigger: {label}")
        if vital_signs.temperature_celsius is not None:
            points, label = temperature_points(vital_signs.temperature_celsius)
            if points >= _MAX_SINGLE_PARAMETER_POINTS:
                triggers.append(f"Single-parameter trigger: {label}")
        if vital_signs.consciousness_level is not None:
            points, label = consciousness_points(vital_signs.consciousness_level)
            if points >= _MAX_SINGLE_PARAMETER_POINTS:
                triggers.append(f"Single-parameter trigger: {label}")
        return tuple(triggers)

    def classify_escalation_urgency(self, risk_score: RiskScore) -> str | None:
        if risk_score.score_value is None:
            return None
        escalation_fn = _ESCALATION_FUNCTIONS.get(risk_score.category)
        if escalation_fn is None:
            return None
        return escalation_fn(risk_score.score_value)
