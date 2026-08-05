"""Unit tests for `CriticalFindingDetectionService`."""

from app.modules.radiology_interpretation_ai.application.services.critical_finding_detection_service import (  # noqa: E501
    CriticalFindingDetectionService,
)
from app.modules.radiology_interpretation_ai.domain.enums import RadiologyFindingCategory
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    FakeFindingExtractionPort,
    make_finding,
)


class TestHasCriticalFindings:
    def test_true_when_any_finding_is_critical(self) -> None:
        service = CriticalFindingDetectionService(extractor=FakeFindingExtractionPort())
        findings = (
            make_finding(category=RadiologyFindingCategory.NORMAL),
            make_finding(category=RadiologyFindingCategory.CRITICAL),
        )
        assert service.has_critical_findings(findings) is True

    def test_false_when_no_finding_is_critical(self) -> None:
        service = CriticalFindingDetectionService(extractor=FakeFindingExtractionPort())
        findings = (make_finding(category=RadiologyFindingCategory.ABNORMAL),)
        assert service.has_critical_findings(findings) is False


class TestEscalateOnCriticalKeywords:
    def test_escalates_when_the_extractor_recognizes_critical_language(self) -> None:
        extractor = FakeFindingExtractionPort(classification=RadiologyFindingCategory.CRITICAL)
        service = CriticalFindingDetectionService(extractor=extractor)
        finding = make_finding(category=RadiologyFindingCategory.ABNORMAL)

        escalated = service.escalate_on_critical_keywords((finding,))

        assert escalated[0].category is RadiologyFindingCategory.CRITICAL

    def test_does_not_downgrade_a_finding_the_ai_already_marked_critical(self) -> None:
        extractor = FakeFindingExtractionPort(classification=None)
        service = CriticalFindingDetectionService(extractor=extractor)
        finding = make_finding(category=RadiologyFindingCategory.CRITICAL)

        escalated = service.escalate_on_critical_keywords((finding,))

        assert escalated[0] is finding
        assert extractor.classify_calls == []

    def test_keeps_the_category_when_the_extractor_does_not_recognize_the_description(
        self,
    ) -> None:
        extractor = FakeFindingExtractionPort(classification=None)
        service = CriticalFindingDetectionService(extractor=extractor)
        finding = make_finding(category=RadiologyFindingCategory.ABNORMAL)

        escalated = service.escalate_on_critical_keywords((finding,))

        assert escalated[0] is finding

    def test_does_not_escalate_to_normal_or_incidental(self) -> None:
        extractor = FakeFindingExtractionPort(classification=RadiologyFindingCategory.NORMAL)
        service = CriticalFindingDetectionService(extractor=extractor)
        finding = make_finding(category=RadiologyFindingCategory.ABNORMAL)

        escalated = service.escalate_on_critical_keywords((finding,))

        assert escalated[0].category is RadiologyFindingCategory.ABNORMAL


class TestDeriveFindingsMissedByAI:
    def test_adds_a_critical_candidate_not_mentioned_by_the_ai(self) -> None:
        service = CriticalFindingDetectionService(extractor=FakeFindingExtractionPort())
        candidates = (
            make_finding(description="Pneumothorax", category=RadiologyFindingCategory.CRITICAL),
        )
        ai_findings = (
            make_finding(description="Clear lungs", category=RadiologyFindingCategory.NORMAL),
        )

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert len(missed) == 1
        assert missed[0].description == "Pneumothorax"

    def test_does_not_duplicate_a_finding_already_mentioned_by_the_ai(self) -> None:
        service = CriticalFindingDetectionService(extractor=FakeFindingExtractionPort())
        candidates = (
            make_finding(description="Pneumothorax", category=RadiologyFindingCategory.CRITICAL),
        )
        ai_findings = (
            make_finding(
                description="Large pneumothorax noted", category=RadiologyFindingCategory.CRITICAL
            ),
        )

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert missed == ()

    def test_ignores_non_critical_candidates(self) -> None:
        service = CriticalFindingDetectionService(extractor=FakeFindingExtractionPort())
        candidates = (
            make_finding(description="Unremarkable", category=RadiologyFindingCategory.NORMAL),
        )
        ai_findings = ()

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert missed == ()

    def test_matching_is_case_insensitive(self) -> None:
        service = CriticalFindingDetectionService(extractor=FakeFindingExtractionPort())
        candidates = (
            make_finding(description="PNEUMOTHORAX", category=RadiologyFindingCategory.CRITICAL),
        )
        ai_findings = (
            make_finding(
                description="pneumothorax present", category=RadiologyFindingCategory.CRITICAL
            ),
        )

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert missed == ()
