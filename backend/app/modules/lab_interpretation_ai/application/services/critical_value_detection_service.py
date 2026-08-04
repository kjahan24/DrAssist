"""`CriticalValueDetectionService` — this task's own explicitly-named
APPLICATION service, and the safety-net half of the "CriticalValueAnalyzerPort"
seam (see that port's own docstring in `application/ports.py`).

The AI's own `LabFinding.flag` classification is trusted by default, but
`reconcile_findings` deterministically **overrides** it whenever
`CriticalValueAnalyzerPort` recognizes the test and the AI's own
classification disagrees — an independent, deterministic cross-check the
same "AI-reported plus a deterministic floor/override, merged" enrichment
shape `app.modules.medical_reasoning_ai.application.services
.evidence_analysis_service.EvidenceAnalysisService.prioritize_red_flags`
establishes for its own module, applied here for patient-safety reasons
specific to lab interpretation: a missed or under-classified critical
value (e.g. a critical potassium the AI reports as merely "abnormal_high")
is exactly the failure mode a deterministic reference-range backstop
exists to catch.
"""

from dataclasses import replace

from app.modules.lab_interpretation_ai.application.ports import CriticalValueAnalyzerPort
from app.modules.lab_interpretation_ai.domain.enums import LabFindingFlag
from app.modules.lab_interpretation_ai.domain.value_objects import LabFinding

_CRITICAL_FLAGS = (LabFindingFlag.CRITICAL_LOW, LabFindingFlag.CRITICAL_HIGH)


class CriticalValueDetectionService:
    def __init__(self, *, analyzer: CriticalValueAnalyzerPort) -> None:
        self._analyzer = analyzer

    def reconcile_findings(self, findings: tuple[LabFinding, ...]) -> tuple[LabFinding, ...]:
        return tuple(self._reconcile_one(finding) for finding in findings)

    def _reconcile_one(self, finding: LabFinding) -> LabFinding:
        deterministic_flag = self._analyzer.classify(
            test_name=finding.test_name, numeric_value=finding.numeric_value
        )
        if deterministic_flag is None or deterministic_flag == finding.flag:
            return finding
        return replace(finding, flag=deterministic_flag)

    def has_critical_values(self, findings: tuple[LabFinding, ...]) -> bool:
        return any(finding.flag in _CRITICAL_FLAGS for finding in findings)
