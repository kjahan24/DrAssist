"""Unit tests for `AlternativeMedicationService`."""

from app.modules.drug_interaction_ai.application.services.alternative_medication_service import (
    AlternativeMedicationService,
)
from app.modules.drug_interaction_ai.domain.enums import SafetySeverity
from tests.unit.modules.drug_interaction_ai.application.fakes import make_issue


class TestFindDuplicate:
    def test_finds_a_case_insensitive_duplicate(self) -> None:
        service = AlternativeMedicationService()
        assert service.find_duplicate(("Monitor INR", "monitor inr")) == "monitor inr"

    def test_returns_none_when_no_duplicate(self) -> None:
        service = AlternativeMedicationService()
        assert service.find_duplicate(("Monitor INR", "Monitor renal function")) is None


class TestDeduplicate:
    def test_keeps_first_occurrence_only(self) -> None:
        service = AlternativeMedicationService()
        result = service.deduplicate(("Monitor INR", "monitor inr", "Monitor renal function"))
        assert result == ("Monitor INR", "Monitor renal function")

    def test_drops_blank_entries(self) -> None:
        service = AlternativeMedicationService()
        assert service.deduplicate(("Monitor INR", "   ")) == ("Monitor INR",)


class TestDeduplicateIssues:
    def test_keeps_first_occurrence_only(self) -> None:
        service = AlternativeMedicationService()
        issue_a = make_issue(description="Bleeding risk")
        issue_b = make_issue(description="bleeding risk")
        issue_c = make_issue(description="QT prolongation risk")

        result = service.deduplicate_issues((issue_a, issue_b, issue_c))

        assert result == (issue_a, issue_c)

    def test_drops_blank_description_entries(self) -> None:
        service = AlternativeMedicationService()
        issue = make_issue(description="   ")
        assert service.deduplicate_issues((issue,)) == ()

    def test_empty_input_returns_empty_tuple(self) -> None:
        service = AlternativeMedicationService()
        assert service.deduplicate_issues(()) == ()


class TestDeriveAlternativesForHighSeverityIssues:
    def test_derives_an_alternative_for_a_major_issue(self) -> None:
        service = AlternativeMedicationService()
        issue = make_issue(severity=SafetySeverity.MAJOR, involved_medications=("Warfarin",))

        alternatives = service.derive_alternatives_for_high_severity_issues((issue,))

        assert len(alternatives) == 1
        assert "Warfarin" in alternatives[0]
        assert "major" in alternatives[0]

    def test_derives_an_alternative_for_a_contraindicated_issue(self) -> None:
        service = AlternativeMedicationService()
        issue = make_issue(severity=SafetySeverity.CONTRAINDICATED)

        alternatives = service.derive_alternatives_for_high_severity_issues((issue,))

        assert len(alternatives) == 1

    def test_no_alternative_for_minor_or_moderate_issues(self) -> None:
        service = AlternativeMedicationService()
        issues = (
            make_issue(severity=SafetySeverity.MINOR),
            make_issue(severity=SafetySeverity.MODERATE),
        )

        assert service.derive_alternatives_for_high_severity_issues(issues) == ()

    def test_falls_back_to_description_when_no_medications_are_involved(self) -> None:
        service = AlternativeMedicationService()
        issue = make_issue(
            severity=SafetySeverity.MAJOR,
            description="Unspecified major concern",
            involved_medications=(),
        )

        alternatives = service.derive_alternatives_for_high_severity_issues((issue,))

        assert "Unspecified major concern" in alternatives[0]
