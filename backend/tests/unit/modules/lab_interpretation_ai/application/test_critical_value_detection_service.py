"""Unit tests for `CriticalValueDetectionService`."""

from app.modules.lab_interpretation_ai.application.services.critical_value_detection_service import (  # noqa: E501
    CriticalValueDetectionService,
)
from app.modules.lab_interpretation_ai.domain.enums import LabFindingFlag
from tests.unit.modules.lab_interpretation_ai.application.fakes import (
    FakeCriticalValueAnalyzerPort,
    make_finding,
)


class TestReconcileFindings:
    def test_overrides_the_ai_flag_when_the_analyzer_disagrees(self) -> None:
        analyzer = FakeCriticalValueAnalyzerPort(classification=LabFindingFlag.CRITICAL_HIGH)
        service = CriticalValueDetectionService(analyzer=analyzer)
        finding = make_finding(flag=LabFindingFlag.ABNORMAL_HIGH)

        reconciled = service.reconcile_findings((finding,))

        assert reconciled[0].flag is LabFindingFlag.CRITICAL_HIGH

    def test_keeps_the_ai_flag_when_the_analyzer_agrees(self) -> None:
        analyzer = FakeCriticalValueAnalyzerPort(classification=LabFindingFlag.NORMAL)
        service = CriticalValueDetectionService(analyzer=analyzer)
        finding = make_finding(flag=LabFindingFlag.NORMAL)

        reconciled = service.reconcile_findings((finding,))

        assert reconciled[0] is finding

    def test_keeps_the_ai_flag_when_the_analyzer_does_not_recognize_the_test(self) -> None:
        analyzer = FakeCriticalValueAnalyzerPort(classification=None)
        service = CriticalValueDetectionService(analyzer=analyzer)
        finding = make_finding(flag=LabFindingFlag.ABNORMAL_HIGH)

        reconciled = service.reconcile_findings((finding,))

        assert reconciled[0] is finding

    def test_passes_test_name_and_numeric_value_to_the_analyzer(self) -> None:
        analyzer = FakeCriticalValueAnalyzerPort()
        service = CriticalValueDetectionService(analyzer=analyzer)
        finding = make_finding(test_name="Glucose", numeric_value=410.0)

        service.reconcile_findings((finding,))

        assert analyzer.calls[0] == {"test_name": "Glucose", "numeric_value": 410.0}


class TestHasCriticalValues:
    def test_true_when_any_finding_is_critical(self) -> None:
        service = CriticalValueDetectionService(analyzer=FakeCriticalValueAnalyzerPort())
        findings = (
            make_finding(flag=LabFindingFlag.NORMAL),
            make_finding(flag=LabFindingFlag.CRITICAL_LOW),
        )
        assert service.has_critical_values(findings) is True

    def test_false_when_no_finding_is_critical(self) -> None:
        service = CriticalValueDetectionService(analyzer=FakeCriticalValueAnalyzerPort())
        findings = (make_finding(flag=LabFindingFlag.NORMAL),)
        assert service.has_critical_values(findings) is False
