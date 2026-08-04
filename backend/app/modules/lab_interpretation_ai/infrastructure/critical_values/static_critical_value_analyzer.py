"""`StaticCriticalValueAnalyzer` — the one concrete
`CriticalValueAnalyzerPort` implementation this task ships: a small,
curated, generic-adult reference-range table keyed by normalized test
name. A real production system might instead consult a structured,
age/sex-adjusted clinical reference database here; this module's own
small, table-driven implementation is the pragmatic in-repo substitute,
the same "each module defines its own local, necessarily-incomplete
copy" precedent `app.modules.icd10_ai`'s `StaticICD10KnowledgeBase` and
`app.modules.prescription_ai`'s `StaticMedicationKnowledgeBase` already
establish for their own modules.

Each table entry is a `_ReferenceRange`: `critical_low`/`critical_high`
are `None` when that side has no clinically meaningful "critical"
threshold for the test (e.g. a low LDL cholesterol is not a critical
value) — `classify` then only ever reports `ABNORMAL_LOW`/`ABNORMAL_HIGH`
on that side, never a critical flag it has no threshold for.
"""

from dataclasses import dataclass

from app.modules.lab_interpretation_ai.application.ports import CriticalValueAnalyzerPort
from app.modules.lab_interpretation_ai.domain.enums import LabFindingFlag


@dataclass(frozen=True, slots=True)
class _ReferenceRange:
    normal_low: float
    normal_high: float
    critical_low: float | None = None
    critical_high: float | None = None


_REFERENCE_RANGES: dict[str, _ReferenceRange] = {
    "hemoglobin": _ReferenceRange(normal_low=12.0, normal_high=17.5, critical_low=7.0),
    "hematocrit": _ReferenceRange(normal_low=36.0, normal_high=52.0, critical_low=20.0),
    "wbc": _ReferenceRange(normal_low=4.5, normal_high=11.0, critical_low=1.0, critical_high=30.0),
    "white blood cell count": _ReferenceRange(
        normal_low=4.5, normal_high=11.0, critical_low=1.0, critical_high=30.0
    ),
    "platelets": _ReferenceRange(
        normal_low=150.0, normal_high=450.0, critical_low=20.0, critical_high=1000.0
    ),
    "sodium": _ReferenceRange(
        normal_low=135.0, normal_high=145.0, critical_low=120.0, critical_high=160.0
    ),
    "potassium": _ReferenceRange(
        normal_low=3.5, normal_high=5.0, critical_low=2.5, critical_high=6.5
    ),
    "chloride": _ReferenceRange(normal_low=96.0, normal_high=106.0),
    "co2": _ReferenceRange(normal_low=23.0, normal_high=29.0, critical_low=10.0),
    "bicarbonate": _ReferenceRange(normal_low=23.0, normal_high=29.0, critical_low=10.0),
    "bun": _ReferenceRange(normal_low=7.0, normal_high=20.0, critical_high=100.0),
    "creatinine": _ReferenceRange(normal_low=0.6, normal_high=1.3, critical_high=4.0),
    "calcium": _ReferenceRange(
        normal_low=8.5, normal_high=10.5, critical_low=6.5, critical_high=13.0
    ),
    "glucose": _ReferenceRange(
        normal_low=70.0, normal_high=100.0, critical_low=40.0, critical_high=400.0
    ),
    "hba1c": _ReferenceRange(normal_low=4.0, normal_high=5.6, critical_high=12.0),
    "alt": _ReferenceRange(normal_low=7.0, normal_high=56.0, critical_high=1000.0),
    "ast": _ReferenceRange(normal_low=8.0, normal_high=48.0, critical_high=1000.0),
    "total bilirubin": _ReferenceRange(normal_low=0.1, normal_high=1.2, critical_high=15.0),
    "inr": _ReferenceRange(normal_low=0.8, normal_high=1.1, critical_high=5.0),
    "tsh": _ReferenceRange(normal_low=0.4, normal_high=4.0, critical_low=0.01, critical_high=100.0),
    "crp": _ReferenceRange(normal_low=0.0, normal_high=10.0),
    "ldl cholesterol": _ReferenceRange(normal_low=0.0, normal_high=130.0),
}


class StaticCriticalValueAnalyzer(CriticalValueAnalyzerPort):
    def __init__(self, reference_ranges: dict[str, _ReferenceRange] | None = None) -> None:
        self._reference_ranges = reference_ranges or _REFERENCE_RANGES

    def classify(self, *, test_name: str, numeric_value: float | None) -> LabFindingFlag | None:
        if numeric_value is None:
            return None
        reference_range = self._reference_ranges.get(test_name.strip().lower())
        if reference_range is None:
            return None

        if numeric_value < reference_range.normal_low:
            if (
                reference_range.critical_low is not None
                and numeric_value < reference_range.critical_low
            ):
                return LabFindingFlag.CRITICAL_LOW
            return LabFindingFlag.ABNORMAL_LOW

        if numeric_value > reference_range.normal_high:
            if (
                reference_range.critical_high is not None
                and numeric_value > reference_range.critical_high
            ):
                return LabFindingFlag.CRITICAL_HIGH
            return LabFindingFlag.ABNORMAL_HIGH

        return LabFindingFlag.NORMAL
