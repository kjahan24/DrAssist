"""Unit tests for `LabRecommendationService`."""

from app.modules.lab_interpretation_ai.application.services.lab_recommendation_service import (
    LabRecommendationService,
)
from app.modules.lab_interpretation_ai.domain.enums import LabFindingFlag
from tests.unit.modules.lab_interpretation_ai.application.fakes import make_finding


class TestFindDuplicate:
    def test_finds_a_case_insensitive_duplicate(self) -> None:
        service = LabRecommendationService()
        assert service.find_duplicate(("Repeat CBC", "repeat cbc")) == "repeat cbc"

    def test_returns_none_when_no_duplicate(self) -> None:
        service = LabRecommendationService()
        assert service.find_duplicate(("Repeat CBC", "Repeat BMP")) is None


class TestDeduplicate:
    def test_keeps_first_occurrence_only(self) -> None:
        service = LabRecommendationService()
        result = service.deduplicate(("Repeat CBC", "repeat cbc", "Repeat BMP"))
        assert result == ("Repeat CBC", "Repeat BMP")

    def test_drops_blank_entries(self) -> None:
        service = LabRecommendationService()
        assert service.deduplicate(("Repeat CBC", "   ")) == ("Repeat CBC",)


class TestDeriveFollowUpForCriticalFindings:
    def test_derives_a_repeat_test_for_each_critical_finding(self) -> None:
        service = LabRecommendationService()
        findings = (
            make_finding(test_name="Potassium", flag=LabFindingFlag.CRITICAL_HIGH),
            make_finding(test_name="Sodium", flag=LabFindingFlag.NORMAL),
            make_finding(test_name="Glucose", flag=LabFindingFlag.CRITICAL_LOW),
        )

        follow_ups = service.derive_follow_up_for_critical_findings(findings)

        assert follow_ups == (
            "Repeat Potassium to confirm critical result",
            "Repeat Glucose to confirm critical result",
        )

    def test_empty_when_no_critical_findings(self) -> None:
        service = LabRecommendationService()
        findings = (make_finding(flag=LabFindingFlag.ABNORMAL_HIGH),)
        assert service.derive_follow_up_for_critical_findings(findings) == ()
