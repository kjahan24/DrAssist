"""Unit tests for `ClinicalCorrelationService`."""

from app.modules.pathology_interpretation_ai.application.services.clinical_correlation_service import (  # noqa: E501
    ClinicalCorrelationService,
)
from app.modules.pathology_interpretation_ai.domain.enums import PathologyFindingCategory
from tests.unit.modules.pathology_interpretation_ai.application.fakes import make_finding


class TestFindDuplicate:
    def test_finds_a_case_insensitive_duplicate(self) -> None:
        service = ClinicalCorrelationService()
        assert service.find_duplicate(("Repeat biopsy", "repeat biopsy")) == "repeat biopsy"

    def test_returns_none_when_no_duplicate(self) -> None:
        service = ClinicalCorrelationService()
        assert service.find_duplicate(("Repeat biopsy", "IHC panel")) is None


class TestDeduplicate:
    def test_keeps_first_occurrence_only(self) -> None:
        service = ClinicalCorrelationService()
        result = service.deduplicate(("Repeat biopsy", "repeat biopsy", "IHC panel"))
        assert result == ("Repeat biopsy", "IHC panel")

    def test_drops_blank_entries(self) -> None:
        service = ClinicalCorrelationService()
        assert service.deduplicate(("Repeat biopsy", "   ")) == ("Repeat biopsy",)


class TestDeriveCorrelationRecommendationsForMalignantFindings:
    def test_derives_a_correlation_recommendation_for_each_malignant_finding(self) -> None:
        service = ClinicalCorrelationService()
        findings = (
            make_finding(
                description="Invasive carcinoma", category=PathologyFindingCategory.MALIGNANT
            ),
            make_finding(description="Benign tissue", category=PathologyFindingCategory.BENIGN),
        )

        recommendations = service.derive_correlation_recommendations_for_malignant_findings(
            findings
        )

        assert recommendations == (
            "Ancillary study correlation (IHC/molecular) recommended for: Invasive carcinoma",
        )

    def test_empty_when_no_malignant_findings(self) -> None:
        service = ClinicalCorrelationService()
        findings = (make_finding(category=PathologyFindingCategory.ATYPICAL),)
        assert service.derive_correlation_recommendations_for_malignant_findings(findings) == ()


class TestDeriveFollowUpForMalignantFindings:
    def test_derives_follow_up_for_each_malignant_finding(self) -> None:
        service = ClinicalCorrelationService()
        findings = (
            make_finding(
                description="Invasive carcinoma", category=PathologyFindingCategory.MALIGNANT
            ),
        )

        follow_ups = service.derive_follow_up_for_malignant_findings(findings)

        assert follow_ups == (
            "Confirmatory follow-up recommended for malignant finding: Invasive carcinoma",
        )

    def test_empty_when_no_malignant_findings(self) -> None:
        service = ClinicalCorrelationService()
        findings = (make_finding(category=PathologyFindingCategory.BENIGN),)
        assert service.derive_follow_up_for_malignant_findings(findings) == ()


class TestDeriveSpecialistReferralForMalignantFindings:
    def test_derives_a_referral_for_each_malignant_finding(self) -> None:
        service = ClinicalCorrelationService()
        findings = (
            make_finding(
                description="Invasive carcinoma", category=PathologyFindingCategory.MALIGNANT
            ),
        )

        referrals = service.derive_specialist_referral_for_malignant_findings(findings)

        assert referrals == (
            "Urgent oncology referral recommended given malignant finding: Invasive carcinoma",
        )

    def test_empty_when_no_malignant_findings(self) -> None:
        service = ClinicalCorrelationService()
        findings = (make_finding(category=PathologyFindingCategory.ATYPICAL),)
        assert service.derive_specialist_referral_for_malignant_findings(findings) == ()
