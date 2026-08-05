"""`StandardRiskScoringCalculator` — the one concrete `RiskScoringPort`
implementation this task ships: computes NEWS2, MEWS, and qSOFA exactly
per their real, publicly-documented point tables (Royal College of
Physicians NEWS2; the widely-published Modified Early Warning Score;
Seymour et al.'s quick SOFA), and a simplified SOFA proxy — see
`RiskScoringPort.compute_sofa_simplified`'s own docstring for why real
SOFA cannot be computed from this task's own SUPPORTED INPUT and what
proxy is substituted instead.

Every `compute_*` method returns `None`, never a fabricated partial
score, when `vital_signs` lacks the specific parameters that score
requires. One assumption is made uniformly across all three standardized
scores that need it: `on_supplemental_oxygen=None` is treated as "room
air" (`False`) rather than "unknown" — vital-sign charting overwhelmingly
defaults to room air when oxygen therapy is not separately documented,
and NEWS2's own official chart is itself a printed form where this field
defaults unchecked.
"""

from app.modules.risk_stratification_ai.application.ports import RiskScoringPort
from app.modules.risk_stratification_ai.domain.enums import ConsciousnessLevel, RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import (
    LabValue,
    RiskScore,
    VitalSigns,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    consciousness_points as news2_consciousness_points,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    heart_rate_points as news2_heart_rate_points,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    oxygen_saturation_points as news2_oxygen_saturation_points,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    respiratory_rate_points as news2_respiratory_rate_points,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    systolic_bp_points as news2_systolic_bp_points,
)
from app.modules.risk_stratification_ai.infrastructure.clinical_scoring.news2_parameters import (
    temperature_points as news2_temperature_points,
)


def _supplemental_oxygen_points(on_supplemental_oxygen: bool | None) -> tuple[int, str]:
    if on_supplemental_oxygen:
        return 2, "On supplemental oxygen"
    return 0, "On room air"


def _mews_systolic_bp_points(systolic_bp: int) -> tuple[int, str]:
    if systolic_bp <= 70:
        return 3, f"Systolic BP {systolic_bp} mmHg (very low)"
    if systolic_bp <= 80:
        return 2, f"Systolic BP {systolic_bp} mmHg (low)"
    if systolic_bp <= 100:
        return 1, f"Systolic BP {systolic_bp} mmHg (mildly low)"
    if systolic_bp <= 199:
        return 0, f"Systolic BP {systolic_bp} mmHg (normal)"
    return 2, f"Systolic BP {systolic_bp} mmHg (high)"


def _mews_heart_rate_points(heart_rate: int) -> tuple[int, str]:
    if heart_rate <= 40:
        return 2, f"Heart rate {heart_rate}/min (low)"
    if heart_rate <= 50:
        return 1, f"Heart rate {heart_rate}/min (mildly low)"
    if heart_rate <= 100:
        return 0, f"Heart rate {heart_rate}/min (normal)"
    if heart_rate <= 110:
        return 1, f"Heart rate {heart_rate}/min (mildly high)"
    if heart_rate <= 129:
        return 2, f"Heart rate {heart_rate}/min (high)"
    return 3, f"Heart rate {heart_rate}/min (very high)"


def _mews_respiratory_rate_points(respiratory_rate: int) -> tuple[int, str]:
    if respiratory_rate < 9:
        return 2, f"Respiratory rate {respiratory_rate}/min (low)"
    if respiratory_rate <= 14:
        return 0, f"Respiratory rate {respiratory_rate}/min (normal)"
    if respiratory_rate <= 20:
        return 1, f"Respiratory rate {respiratory_rate}/min (mildly high)"
    if respiratory_rate <= 29:
        return 2, f"Respiratory rate {respiratory_rate}/min (high)"
    return 3, f"Respiratory rate {respiratory_rate}/min (very high)"


def _mews_temperature_points(temperature_celsius: float) -> tuple[int, str]:
    if temperature_celsius < 35.0:
        return 2, f"Temperature {temperature_celsius:g}C (low)"
    if temperature_celsius <= 38.4:
        return 0, f"Temperature {temperature_celsius:g}C (normal)"
    return 2, f"Temperature {temperature_celsius:g}C (high)"


def _mews_consciousness_points(consciousness_level: ConsciousnessLevel) -> tuple[int, str]:
    mapping = {
        ConsciousnessLevel.ALERT: 0,
        ConsciousnessLevel.VOICE: 1,
        ConsciousnessLevel.PAIN: 2,
        ConsciousnessLevel.UNRESPONSIVE: 3,
    }
    return mapping[consciousness_level], f"Consciousness level: {consciousness_level.value}"


def _sofa_respiratory_points(oxygen_saturation: float) -> tuple[int, str]:
    if oxygen_saturation >= 95:
        return 0, f"SpO2 {oxygen_saturation:g}% (normal)"
    if oxygen_saturation >= 90:
        return 1, f"SpO2 {oxygen_saturation:g}% (mildly low)"
    return 2, f"SpO2 {oxygen_saturation:g}% (low)"


def _sofa_cardiovascular_points(systolic_bp: int) -> tuple[int, str]:
    if systolic_bp >= 100:
        return 0, f"Systolic BP {systolic_bp} mmHg (normal)"
    if systolic_bp >= 90:
        return 1, f"Systolic BP {systolic_bp} mmHg (mildly low)"
    return 2, f"Systolic BP {systolic_bp} mmHg (low)"


def _sofa_cns_points(consciousness_level: ConsciousnessLevel) -> tuple[int, str]:
    mapping = {
        ConsciousnessLevel.ALERT: 0,
        ConsciousnessLevel.VOICE: 1,
        ConsciousnessLevel.PAIN: 1,
        ConsciousnessLevel.UNRESPONSIVE: 2,
    }
    return mapping[consciousness_level], f"Consciousness level: {consciousness_level.value}"


def _find_creatinine_value(lab_values: tuple[LabValue, ...]) -> float | None:
    for lab in lab_values:
        if "creatinine" in lab.test_name.strip().lower() and lab.numeric_value is not None:
            return lab.numeric_value
    return None


def _sofa_renal_points(creatinine: float) -> tuple[int, str]:
    if creatinine >= 2.0:
        return 2, f"Creatinine {creatinine:g} mg/dL (high)"
    if creatinine >= 1.2:
        return 1, f"Creatinine {creatinine:g} mg/dL (mildly high)"
    return 0, f"Creatinine {creatinine:g} mg/dL (normal)"


class StandardRiskScoringCalculator(RiskScoringPort):
    def compute_news2(self, vital_signs: VitalSigns) -> RiskScore | None:
        if (
            vital_signs.respiratory_rate is None
            or vital_signs.oxygen_saturation is None
            or vital_signs.systolic_bp is None
            or vital_signs.heart_rate is None
            or vital_signs.temperature_celsius is None
            or vital_signs.consciousness_level is None
        ):
            return None

        components = (
            news2_respiratory_rate_points(vital_signs.respiratory_rate),
            news2_oxygen_saturation_points(vital_signs.oxygen_saturation),
            _supplemental_oxygen_points(vital_signs.on_supplemental_oxygen),
            news2_systolic_bp_points(vital_signs.systolic_bp),
            news2_heart_rate_points(vital_signs.heart_rate),
            news2_temperature_points(vital_signs.temperature_celsius),
            news2_consciousness_points(vital_signs.consciousness_level),
        )
        total = sum(points for points, _ in components)
        factors = tuple(label for points, label in components if points > 0)
        return RiskScore(
            category=RiskCategory.NEWS2,
            score_value=float(total),
            contributing_factors=factors,
            clinical_explanation=(
                f"NEWS2 score of {total}, computed from respiratory rate, oxygen saturation, "
                "supplemental oxygen use, systolic blood pressure, heart rate, temperature, "
                "and consciousness level."
            ),
        )

    def compute_mews(self, vital_signs: VitalSigns) -> RiskScore | None:
        if (
            vital_signs.systolic_bp is None
            or vital_signs.heart_rate is None
            or vital_signs.respiratory_rate is None
            or vital_signs.temperature_celsius is None
            or vital_signs.consciousness_level is None
        ):
            return None

        components = (
            _mews_systolic_bp_points(vital_signs.systolic_bp),
            _mews_heart_rate_points(vital_signs.heart_rate),
            _mews_respiratory_rate_points(vital_signs.respiratory_rate),
            _mews_temperature_points(vital_signs.temperature_celsius),
            _mews_consciousness_points(vital_signs.consciousness_level),
        )
        total = sum(points for points, _ in components)
        factors = tuple(label for points, label in components if points > 0)
        return RiskScore(
            category=RiskCategory.MEWS,
            score_value=float(total),
            contributing_factors=factors,
            clinical_explanation=(
                f"MEWS score of {total}, computed from systolic blood pressure, heart rate, "
                "respiratory rate, temperature, and consciousness level."
            ),
        )

    def compute_qsofa(self, vital_signs: VitalSigns) -> RiskScore | None:
        if (
            vital_signs.respiratory_rate is None
            or vital_signs.systolic_bp is None
            or vital_signs.consciousness_level is None
        ):
            return None

        factors: list[str] = []
        total = 0
        if vital_signs.respiratory_rate >= 22:
            total += 1
            factors.append(f"Respiratory rate {vital_signs.respiratory_rate}/min (>= 22)")
        if vital_signs.systolic_bp <= 100:
            total += 1
            factors.append(f"Systolic BP {vital_signs.systolic_bp} mmHg (<= 100)")
        if vital_signs.consciousness_level is not ConsciousnessLevel.ALERT:
            total += 1
            factors.append(f"Altered mentation ({vital_signs.consciousness_level.value})")

        return RiskScore(
            category=RiskCategory.QSOFA,
            score_value=float(total),
            contributing_factors=tuple(factors),
            clinical_explanation=(
                f"qSOFA score of {total}, computed from respiratory rate, systolic blood "
                "pressure, and mentation. A score of 2 or more suggests an increased risk of "
                "poor outcome from suspected infection."
            ),
        )

    def compute_sofa_simplified(
        self, vital_signs: VitalSigns, lab_values: tuple[LabValue, ...]
    ) -> RiskScore | None:
        if (
            vital_signs.oxygen_saturation is None
            or vital_signs.systolic_bp is None
            or vital_signs.consciousness_level is None
        ):
            return None

        components = [
            _sofa_respiratory_points(vital_signs.oxygen_saturation),
            _sofa_cardiovascular_points(vital_signs.systolic_bp),
            _sofa_cns_points(vital_signs.consciousness_level),
        ]
        creatinine = _find_creatinine_value(lab_values)
        if creatinine is not None:
            components.append(_sofa_renal_points(creatinine))

        total = sum(points for points, _ in components)
        factors = tuple(label for points, label in components if points > 0)
        return RiskScore(
            category=RiskCategory.SOFA_SIMPLIFIED,
            score_value=float(total),
            contributing_factors=factors,
            clinical_explanation=(
                f"Simplified SOFA score of {total} (0-8 range), a deliberate simplification "
                "of the real 0-24 SOFA score that substitutes SpO2 for the PaO2/FiO2 ratio, "
                "systolic blood pressure for mean arterial pressure and vasopressor dose, and "
                "AVPU consciousness level for the Glasgow Coma Scale — the real bilirubin, "
                "platelet, and vasopressor inputs are not part of this task's own SUPPORTED "
                "INPUT and are not fabricated here."
            ),
        )
