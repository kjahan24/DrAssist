"""Unit tests for `MedicationSafetyService`."""

from app.modules.drug_interaction_ai.application.services.medication_safety_service import (
    MedicationSafetyService,
)
from app.modules.drug_interaction_ai.domain.enums import SafetyIssueCategory
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    FakeMedicationSafetyPort,
    make_issue,
    make_medication,
)


class TestDetectPatientContextRisks:
    def test_delegates_per_medication_to_the_port(self) -> None:
        port = FakeMedicationSafetyPort()
        service = MedicationSafetyService(port=port)
        medications = (make_medication(drug_name="A"), make_medication(drug_name="B"))

        service.detect_patient_context_risks(
            medications,
            allergies=(),
            medical_conditions=(),
            pregnancy_status=None,
            lactation_status=None,
            patient_age=None,
        )

        assert len(port.context_risk_calls) == 2

    def test_collects_issues_from_every_medication(self) -> None:
        issue = make_issue(category=SafetyIssueCategory.DRUG_ALLERGY_INTERACTION)
        port = FakeMedicationSafetyPort(context_risks=(issue,))
        service = MedicationSafetyService(port=port)
        medications = (make_medication(drug_name="A"), make_medication(drug_name="B"))

        issues = service.detect_patient_context_risks(
            medications,
            allergies=(),
            medical_conditions=(),
            pregnancy_status=None,
            lactation_status=None,
            patient_age=None,
        )

        assert issues == (issue, issue)


class TestDetectPharmacologicRiskFlags:
    def test_returns_empty_when_no_flags(self) -> None:
        service = MedicationSafetyService(port=FakeMedicationSafetyPort())
        assert service.detect_pharmacologic_risk_flags((make_medication(),)) == ()

    def test_wraps_each_flag_into_a_safety_issue(self) -> None:
        port = FakeMedicationSafetyPort(
            risk_flags=(
                SafetyIssueCategory.QT_PROLONGATION_RISK,
                SafetyIssueCategory.BLEEDING_RISK,
            )
        )
        service = MedicationSafetyService(port=port)

        issues = service.detect_pharmacologic_risk_flags((make_medication(drug_name="Warfarin"),))

        categories = {issue.category for issue in issues}
        assert categories == {
            SafetyIssueCategory.QT_PROLONGATION_RISK,
            SafetyIssueCategory.BLEEDING_RISK,
        }
        assert all(issue.involved_medications == ("Warfarin",) for issue in issues)


class TestDetectReconciliationIssues:
    def test_no_issue_for_a_single_entry(self) -> None:
        service = MedicationSafetyService(port=FakeMedicationSafetyPort())
        assert service.detect_reconciliation_issues((make_medication(),)) == ()

    def test_no_issue_when_the_same_drug_has_identical_details(self) -> None:
        service = MedicationSafetyService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin", dose="5mg"),
            make_medication(drug_name="Warfarin", dose="5mg"),
        )
        assert service.detect_reconciliation_issues(medications) == ()

    def test_flags_when_the_same_drug_has_conflicting_dose(self) -> None:
        service = MedicationSafetyService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin", dose="5mg"),
            make_medication(drug_name="Warfarin", dose="10mg"),
        )

        issues = service.detect_reconciliation_issues(medications)

        assert len(issues) == 1
        assert issues[0].category is SafetyIssueCategory.MEDICATION_RECONCILIATION_ISSUE

    def test_is_case_insensitive_on_drug_name(self) -> None:
        service = MedicationSafetyService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin", dose="5mg"),
            make_medication(drug_name="warfarin", dose="10mg"),
        )

        issues = service.detect_reconciliation_issues(medications)

        assert len(issues) == 1

    def test_does_not_double_flag_the_same_conflicting_drug(self) -> None:
        service = MedicationSafetyService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin", dose="5mg"),
            make_medication(drug_name="Warfarin", dose="10mg"),
            make_medication(drug_name="Warfarin", dose="15mg"),
        )

        issues = service.detect_reconciliation_issues(medications)

        assert len(issues) == 1

    def test_no_issue_for_two_different_drugs(self) -> None:
        service = MedicationSafetyService(port=FakeMedicationSafetyPort())
        medications = (
            make_medication(drug_name="Warfarin", dose="5mg"),
            make_medication(drug_name="Aspirin", dose="81mg"),
        )
        assert service.detect_reconciliation_issues(medications) == ()
