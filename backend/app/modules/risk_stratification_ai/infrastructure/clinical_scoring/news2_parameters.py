"""The six per-parameter NEWS2 point functions (Royal College of
Physicians NEWS2 chart), shared by `standard_risk_scoring_calculator.py`
(which sums them into the aggregate NEWS2 total) and
`infrastructure/early_warning/standard_early_warning_analyzer.py` (which
surfaces any single parameter that scored the maximum 3 points on its
own, per NEWS2's own official single-parameter escalation rule) —
factored out into their own module, rather than one importing the
other's private helpers, so both call sites depend on one clearly public
seam.
"""

from app.modules.risk_stratification_ai.domain.enums import ConsciousnessLevel


def respiratory_rate_points(respiratory_rate: int) -> tuple[int, str]:
    if respiratory_rate <= 8:
        return 3, f"Respiratory rate {respiratory_rate}/min (very low)"
    if respiratory_rate <= 11:
        return 1, f"Respiratory rate {respiratory_rate}/min (low)"
    if respiratory_rate <= 20:
        return 0, f"Respiratory rate {respiratory_rate}/min (normal)"
    if respiratory_rate <= 24:
        return 2, f"Respiratory rate {respiratory_rate}/min (elevated)"
    return 3, f"Respiratory rate {respiratory_rate}/min (very high)"


def oxygen_saturation_points(oxygen_saturation: float) -> tuple[int, str]:
    if oxygen_saturation <= 91:
        return 3, f"SpO2 {oxygen_saturation:g}% (severely low)"
    if oxygen_saturation <= 93:
        return 2, f"SpO2 {oxygen_saturation:g}% (low)"
    if oxygen_saturation <= 95:
        return 1, f"SpO2 {oxygen_saturation:g}% (mildly low)"
    return 0, f"SpO2 {oxygen_saturation:g}% (normal)"


def systolic_bp_points(systolic_bp: int) -> tuple[int, str]:
    if systolic_bp <= 90:
        return 3, f"Systolic BP {systolic_bp} mmHg (very low)"
    if systolic_bp <= 100:
        return 2, f"Systolic BP {systolic_bp} mmHg (low)"
    if systolic_bp <= 110:
        return 1, f"Systolic BP {systolic_bp} mmHg (mildly low)"
    if systolic_bp <= 219:
        return 0, f"Systolic BP {systolic_bp} mmHg (normal)"
    return 3, f"Systolic BP {systolic_bp} mmHg (very high)"


def heart_rate_points(heart_rate: int) -> tuple[int, str]:
    if heart_rate <= 40:
        return 3, f"Heart rate {heart_rate}/min (very low)"
    if heart_rate <= 50:
        return 1, f"Heart rate {heart_rate}/min (low)"
    if heart_rate <= 90:
        return 0, f"Heart rate {heart_rate}/min (normal)"
    if heart_rate <= 110:
        return 1, f"Heart rate {heart_rate}/min (mildly high)"
    if heart_rate <= 130:
        return 2, f"Heart rate {heart_rate}/min (high)"
    return 3, f"Heart rate {heart_rate}/min (very high)"


def temperature_points(temperature_celsius: float) -> tuple[int, str]:
    if temperature_celsius <= 35.0:
        return 3, f"Temperature {temperature_celsius:g}C (very low)"
    if temperature_celsius <= 36.0:
        return 1, f"Temperature {temperature_celsius:g}C (low)"
    if temperature_celsius <= 38.0:
        return 0, f"Temperature {temperature_celsius:g}C (normal)"
    if temperature_celsius <= 39.0:
        return 1, f"Temperature {temperature_celsius:g}C (mildly high)"
    return 2, f"Temperature {temperature_celsius:g}C (high)"


def consciousness_points(consciousness_level: ConsciousnessLevel) -> tuple[int, str]:
    if consciousness_level is ConsciousnessLevel.ALERT:
        return 0, "Alert"
    return 3, f"Not alert ({consciousness_level.value})"
