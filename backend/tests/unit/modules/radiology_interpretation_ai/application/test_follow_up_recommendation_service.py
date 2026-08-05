"""Unit tests for `FollowUpRecommendationService`."""

from app.modules.radiology_interpretation_ai.application.services.follow_up_recommendation_service import (  # noqa: E501
    FollowUpRecommendationService,
)
from app.modules.radiology_interpretation_ai.domain.enums import RadiologyFindingCategory
from tests.unit.modules.radiology_interpretation_ai.application.fakes import make_finding


class TestFindDuplicate:
    def test_finds_a_case_insensitive_duplicate(self) -> None:
        service = FollowUpRecommendationService()
        assert service.find_duplicate(("Repeat CT", "repeat ct")) == "repeat ct"

    def test_returns_none_when_no_duplicate(self) -> None:
        service = FollowUpRecommendationService()
        assert service.find_duplicate(("Repeat CT", "Repeat MRI")) is None


class TestDeduplicate:
    def test_keeps_first_occurrence_only(self) -> None:
        service = FollowUpRecommendationService()
        result = service.deduplicate(("Repeat CT", "repeat ct", "Repeat MRI"))
        assert result == ("Repeat CT", "Repeat MRI")

    def test_drops_blank_entries(self) -> None:
        service = FollowUpRecommendationService()
        assert service.deduplicate(("Repeat CT", "   ")) == ("Repeat CT",)


class TestDeriveFollowUpForCriticalFindings:
    def test_derives_follow_up_for_each_critical_finding(self) -> None:
        service = FollowUpRecommendationService()
        findings = (
            make_finding(
                description="Large pneumothorax", category=RadiologyFindingCategory.CRITICAL
            ),
            make_finding(description="Clear lungs", category=RadiologyFindingCategory.NORMAL),
        )

        follow_ups = service.derive_follow_up_for_critical_findings(findings)

        assert follow_ups == ("Further imaging correlation recommended for: Large pneumothorax",)

    def test_empty_when_no_critical_findings(self) -> None:
        service = FollowUpRecommendationService()
        findings = (make_finding(category=RadiologyFindingCategory.ABNORMAL),)
        assert service.derive_follow_up_for_critical_findings(findings) == ()


class TestDeriveSpecialistReferralForCriticalFindings:
    def test_derives_a_referral_for_each_critical_finding(self) -> None:
        service = FollowUpRecommendationService()
        findings = (
            make_finding(
                description="Large pneumothorax", category=RadiologyFindingCategory.CRITICAL
            ),
        )

        referrals = service.derive_specialist_referral_for_critical_findings(findings)

        assert referrals == (
            "Urgent specialist referral recommended given critical finding: Large pneumothorax",
        )

    def test_empty_when_no_critical_findings(self) -> None:
        service = FollowUpRecommendationService()
        findings = (make_finding(category=RadiologyFindingCategory.INCIDENTAL),)
        assert service.derive_specialist_referral_for_critical_findings(findings) == ()
