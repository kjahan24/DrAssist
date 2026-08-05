"""`EarlyWarningService` — this task's own explicitly-named APPLICATION
service, covering three related deterministic concerns that all draw on
standardized-score thresholds:

- `identify_early_warning_indicators` — thin delegation to
  `EarlyWarningPort.identify_single_parameter_triggers`, this task's own
  "Early Warning Indicators" OUTPUT field: the standard NEWS2-style
  clinical rule that a single grossly abnormal vital sign parameter
  warrants attention even when the aggregate score does not.
- `identify_red_flags` — this task's own "Red Flag Alerts" OUTPUT field:
  every single-parameter trigger, plus a flag for any standardized
  `RiskScore` whose value crosses this service's own `CRITICAL`
  threshold (see `determine_minimum_risk_level` below) — deliberately
  reusing the same threshold table so "red flag" and "this pushed the
  floor to CRITICAL" never disagree with each other.
- `determine_minimum_risk_level` — the "deterministic floor/override"
  safety net this module applies to its OWN top-level
  `overall_risk_level` field (see `application/use_cases
  /analyze_patient_risk.py`'s own module docstring), rather than trusting
  the AI's own reported level unconditionally: computes a deterministic
  minimum from whichever standardized scores (`NEWS2`/`MEWS`/`QSOFA`/
  `SOFA_SIMPLIFIED`) were actually computed, using each score's own
  well-known clinical escalation thresholds, and returns the single
  highest floor across all of them (or `None` when no standardized score
  was computed, in which case the AI's own reported level is trusted
  as-is).
"""

from app.modules.risk_stratification_ai.application.ports import EarlyWarningPort
from app.modules.risk_stratification_ai.domain.enums import OverallRiskLevel, RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import RiskScore, VitalSigns

_LEVEL_RANK: dict[OverallRiskLevel, int] = {
    OverallRiskLevel.LOW: 0,
    OverallRiskLevel.MODERATE: 1,
    OverallRiskLevel.HIGH: 2,
    OverallRiskLevel.CRITICAL: 3,
}


def _floor_from_news2(score_value: float) -> OverallRiskLevel:
    if score_value >= 7:
        return OverallRiskLevel.CRITICAL
    if score_value >= 5:
        return OverallRiskLevel.HIGH
    if score_value >= 1:
        return OverallRiskLevel.MODERATE
    return OverallRiskLevel.LOW


def _floor_from_mews(score_value: float) -> OverallRiskLevel:
    if score_value >= 5:
        return OverallRiskLevel.HIGH
    if score_value >= 3:
        return OverallRiskLevel.MODERATE
    return OverallRiskLevel.LOW


def _floor_from_qsofa(score_value: float) -> OverallRiskLevel:
    if score_value >= 2:
        return OverallRiskLevel.HIGH
    return OverallRiskLevel.LOW


def _floor_from_sofa_simplified(score_value: float) -> OverallRiskLevel:
    if score_value >= 5:
        return OverallRiskLevel.CRITICAL
    if score_value >= 3:
        return OverallRiskLevel.HIGH
    if score_value >= 1:
        return OverallRiskLevel.MODERATE
    return OverallRiskLevel.LOW


_FLOOR_FUNCTIONS = {
    RiskCategory.NEWS2: _floor_from_news2,
    RiskCategory.MEWS: _floor_from_mews,
    RiskCategory.QSOFA: _floor_from_qsofa,
    RiskCategory.SOFA_SIMPLIFIED: _floor_from_sofa_simplified,
}


class EarlyWarningService:
    def __init__(self, *, early_warning_port: EarlyWarningPort) -> None:
        self._early_warning_port = early_warning_port

    def identify_early_warning_indicators(self, vital_signs: VitalSigns) -> tuple[str, ...]:
        return self._early_warning_port.identify_single_parameter_triggers(vital_signs)

    def identify_red_flags(
        self, vital_signs: VitalSigns, risk_scores: tuple[RiskScore, ...]
    ) -> tuple[str, ...]:
        flags = list(self._early_warning_port.identify_single_parameter_triggers(vital_signs))
        for score in risk_scores:
            floor_fn = _FLOOR_FUNCTIONS.get(score.category)
            if floor_fn is None or score.score_value is None:
                continue
            if floor_fn(score.score_value) is OverallRiskLevel.CRITICAL:
                flags.append(
                    f"{score.category.value} score of {score.score_value:g} indicates "
                    "critical risk"
                )
        return tuple(flags)

    def determine_minimum_risk_level(
        self, risk_scores: tuple[RiskScore, ...]
    ) -> OverallRiskLevel | None:
        floors: list[OverallRiskLevel] = []
        for score in risk_scores:
            floor_fn = _FLOOR_FUNCTIONS.get(score.category)
            if floor_fn is None or score.score_value is None:
                continue
            floors.append(floor_fn(score.score_value))
        if not floors:
            return None
        return max(floors, key=lambda level: _LEVEL_RANK[level])

    def apply_deterministic_floor(
        self, ai_reported: OverallRiskLevel, risk_scores: tuple[RiskScore, ...]
    ) -> OverallRiskLevel:
        """This module's own top-level "deterministic floor/override"
        application, per this service's own module docstring: the
        returned level is never *lower* than what the standardized
        scores themselves demand, but may be higher when the AI reported
        a more severe level than the deterministic floor alone would
        require."""
        floor = self.determine_minimum_risk_level(risk_scores)
        if floor is None:
            return ai_reported
        return max(ai_reported, floor, key=lambda level: _LEVEL_RANK[level])
