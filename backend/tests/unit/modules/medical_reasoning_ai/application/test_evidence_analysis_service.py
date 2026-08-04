"""Unit tests for `EvidenceAnalysisService` — the "evidence aggregation,
evidence weighting, conflicting evidence detection, red flag
prioritization, risk scoring, missing-information analysis" half of this
task's own "REASONING ENGINE" section."""

from app.modules.medical_reasoning_ai.application.services.evidence_analysis_service import (
    EvidenceAnalysisService,
)
from app.modules.medical_reasoning_ai.domain.enums import EvidencePolarity, RedFlagPriority
from app.modules.medical_reasoning_ai.domain.value_objects import RedFlag
from tests.unit.modules.medical_reasoning_ai.application.fakes import (
    FakeEvidenceAnalyzerPort,
    make_evidence_item,
)


class TestFindDuplicates:
    def test_flags_the_same_description_appearing_twice(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort())
        items = (
            make_evidence_item(description="Fever present"),
            make_evidence_item(description="Fever present"),
        )

        duplicates = service.find_duplicates(items)

        assert duplicates == ("Fever present",)

    def test_flags_a_duplicate_across_different_polarities(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort())
        items = (
            make_evidence_item(description="Fever present", polarity=EvidencePolarity.SUPPORTING),
            make_evidence_item(
                description="Fever present", polarity=EvidencePolarity.CONTRADICTING
            ),
        )

        duplicates = service.find_duplicates(items)

        assert duplicates == ("Fever present",)

    def test_is_case_and_whitespace_insensitive(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort())
        items = (
            make_evidence_item(description="Fever Present"),
            make_evidence_item(description="  fever present  "),
        )

        duplicates = service.find_duplicates(items)

        assert len(duplicates) == 1

    def test_does_not_flag_genuinely_different_evidence(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort())
        items = (
            make_evidence_item(description="Fever present"),
            make_evidence_item(description="Productive cough"),
        )

        assert service.find_duplicates(items) == ()

    def test_empty_collection_has_no_duplicates(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort())
        assert service.find_duplicates(()) == ()


class TestWeightEvidence:
    def test_delegates_each_item_to_the_analyzer(self) -> None:
        analyzer = FakeEvidenceAnalyzerPort(weight_boost=0.1)
        service = EvidenceAnalysisService(analyzer=analyzer)
        items = (make_evidence_item(weight=0.5),)

        weighted = service.weight_evidence(items)

        assert weighted[0].weight == 0.6
        assert analyzer.weighted_items == [items[0]]


class TestAssessMissingInformation:
    def test_delegates_to_the_analyzer(self) -> None:
        analyzer = FakeEvidenceAnalyzerPort(missing_information=("no labs provided",))
        service = EvidenceAnalysisService(analyzer=analyzer)

        from uuid import uuid4

        from app.modules.medical_reasoning_ai.domain.enums import ReasoningSetting
        from app.modules.medical_reasoning_ai.domain.value_objects import MedicalReasoningInput

        evidence = MedicalReasoningInput(
            organization_id=uuid4(),
            patient_id=uuid4(),
            chief_complaint="Chest pain",
            reasoning_setting=ReasoningSetting.OUTPATIENT,
        )

        missing = service.assess_missing_information(evidence)

        assert missing == ("no labs provided",)
        assert analyzer.missing_information_calls == [evidence]


class TestPrioritizeRedFlags:
    def test_empty_red_flags_returns_empty(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort())
        assert service.prioritize_red_flags(risk_factors=(), red_flags=()) == ()

    def test_sorts_by_priority_severity_descending(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort(risk_score=0.0))
        flags = (
            RedFlag(description="A", priority=RedFlagPriority.LOW),
            RedFlag(description="B", priority=RedFlagPriority.CRITICAL),
            RedFlag(description="C", priority=RedFlagPriority.MODERATE),
        )

        prioritized = service.prioritize_red_flags(risk_factors=(), red_flags=flags)

        assert [f.description for f in prioritized] == ["B", "C", "A"]

    def test_escalates_flags_when_risk_score_is_high(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort(risk_score=0.9))
        flags = (RedFlag(description="A", priority=RedFlagPriority.LOW),)

        prioritized = service.prioritize_red_flags(risk_factors=(), red_flags=flags)

        assert prioritized[0].priority is RedFlagPriority.MODERATE

    def test_does_not_escalate_flags_when_risk_score_is_low(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort(risk_score=0.1))
        flags = (RedFlag(description="A", priority=RedFlagPriority.LOW),)

        prioritized = service.prioritize_red_flags(risk_factors=(), red_flags=flags)

        assert prioritized[0].priority is RedFlagPriority.LOW

    def test_does_not_escalate_a_critical_flag_further(self) -> None:
        service = EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort(risk_score=0.99))
        flags = (RedFlag(description="A", priority=RedFlagPriority.CRITICAL),)

        prioritized = service.prioritize_red_flags(risk_factors=(), red_flags=flags)

        assert prioritized[0].priority is RedFlagPriority.CRITICAL

    def test_passes_risk_factors_and_flags_to_the_analyzer(self) -> None:
        analyzer = FakeEvidenceAnalyzerPort(risk_score=0.0)
        service = EvidenceAnalysisService(analyzer=analyzer)
        flags = (RedFlag(description="A", priority=RedFlagPriority.LOW),)

        service.prioritize_red_flags(risk_factors=("diabetes",), red_flags=flags)

        assert analyzer.risk_score_calls[0]["risk_factors"] == ("diabetes",)
        assert analyzer.risk_score_calls[0]["red_flags"] == flags
