"""Unit tests for `MalignancyAssessmentService`."""

from app.modules.pathology_interpretation_ai.application.services.malignancy_assessment_service import (  # noqa: E501
    MalignancyAssessmentService,
)
from app.modules.pathology_interpretation_ai.domain.enums import PathologyFindingCategory
from tests.unit.modules.pathology_interpretation_ai.application.fakes import (
    FakeClinicalCorrelationPort,
    make_finding,
)


class TestHasMalignantFindings:
    def test_true_when_any_finding_is_malignant(self) -> None:
        service = MalignancyAssessmentService(correlator=FakeClinicalCorrelationPort())
        findings = (
            make_finding(category=PathologyFindingCategory.BENIGN),
            make_finding(category=PathologyFindingCategory.MALIGNANT),
        )
        assert service.has_malignant_findings(findings) is True

    def test_false_when_no_finding_is_malignant(self) -> None:
        service = MalignancyAssessmentService(correlator=FakeClinicalCorrelationPort())
        findings = (make_finding(category=PathologyFindingCategory.ATYPICAL),)
        assert service.has_malignant_findings(findings) is False


class TestEscalateOnMalignantKeywords:
    def test_escalates_when_the_correlator_recognizes_malignant_language(self) -> None:
        correlator = FakeClinicalCorrelationPort(classification=PathologyFindingCategory.MALIGNANT)
        service = MalignancyAssessmentService(correlator=correlator)
        finding = make_finding(category=PathologyFindingCategory.ATYPICAL)

        escalated = service.escalate_on_malignant_keywords((finding,))

        assert escalated[0].category is PathologyFindingCategory.MALIGNANT

    def test_does_not_downgrade_a_finding_the_ai_already_marked_malignant(self) -> None:
        correlator = FakeClinicalCorrelationPort(classification=None)
        service = MalignancyAssessmentService(correlator=correlator)
        finding = make_finding(category=PathologyFindingCategory.MALIGNANT)

        escalated = service.escalate_on_malignant_keywords((finding,))

        assert escalated[0] is finding
        assert correlator.classify_calls == []

    def test_keeps_the_category_when_the_correlator_does_not_recognize_the_description(
        self,
    ) -> None:
        correlator = FakeClinicalCorrelationPort(classification=None)
        service = MalignancyAssessmentService(correlator=correlator)
        finding = make_finding(category=PathologyFindingCategory.ATYPICAL)

        escalated = service.escalate_on_malignant_keywords((finding,))

        assert escalated[0] is finding

    def test_does_not_escalate_to_benign_or_atypical(self) -> None:
        correlator = FakeClinicalCorrelationPort(classification=PathologyFindingCategory.BENIGN)
        service = MalignancyAssessmentService(correlator=correlator)
        finding = make_finding(category=PathologyFindingCategory.ATYPICAL)

        escalated = service.escalate_on_malignant_keywords((finding,))

        assert escalated[0].category is PathologyFindingCategory.ATYPICAL


class TestDeriveFindingsMissedByAI:
    def test_adds_a_malignant_candidate_not_mentioned_by_the_ai(self) -> None:
        service = MalignancyAssessmentService(correlator=FakeClinicalCorrelationPort())
        candidates = (
            make_finding(description="Carcinoma", category=PathologyFindingCategory.MALIGNANT),
        )
        ai_findings = (
            make_finding(description="Reactive changes", category=PathologyFindingCategory.BENIGN),
        )

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert len(missed) == 1
        assert missed[0].description == "Carcinoma"

    def test_does_not_duplicate_a_finding_already_mentioned_by_the_ai(self) -> None:
        service = MalignancyAssessmentService(correlator=FakeClinicalCorrelationPort())
        candidates = (
            make_finding(description="Carcinoma", category=PathologyFindingCategory.MALIGNANT),
        )
        ai_findings = (
            make_finding(
                description="Invasive carcinoma noted", category=PathologyFindingCategory.MALIGNANT
            ),
        )

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert missed == ()

    def test_ignores_non_malignant_candidates(self) -> None:
        service = MalignancyAssessmentService(correlator=FakeClinicalCorrelationPort())
        candidates = (make_finding(description="Benign", category=PathologyFindingCategory.BENIGN),)
        ai_findings = ()

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert missed == ()

    def test_matching_is_case_insensitive(self) -> None:
        service = MalignancyAssessmentService(correlator=FakeClinicalCorrelationPort())
        candidates = (
            make_finding(description="CARCINOMA", category=PathologyFindingCategory.MALIGNANT),
        )
        ai_findings = (
            make_finding(
                description="carcinoma present", category=PathologyFindingCategory.MALIGNANT
            ),
        )

        missed = service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=ai_findings
        )

        assert missed == ()
