"""Unit tests for `DrugInteractionService`."""

from app.modules.drug_interaction_ai.application.services.drug_interaction_service import (
    DrugInteractionService,
)
from app.modules.drug_interaction_ai.domain.enums import EvidenceLevel, SafetyIssueCategory
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    FakeDrugInteractionPort,
    FakeInteractionEvidencePort,
    make_issue,
    make_medication,
)


class TestDetectKnownInteractions:
    def test_returns_empty_tuple_for_a_single_medication(self) -> None:
        service = DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(),
            evidence_port=FakeInteractionEvidencePort(),
        )
        assert service.detect_known_interactions((make_medication(),)) == ()

    def test_checks_every_unique_pair(self) -> None:
        port = FakeDrugInteractionPort()
        service = DrugInteractionService(
            interaction_port=port, evidence_port=FakeInteractionEvidencePort()
        )
        medications = (
            make_medication(drug_name="A"),
            make_medication(drug_name="B"),
            make_medication(drug_name="C"),
        )

        service.detect_known_interactions(medications)

        assert len(port.calls) == 3
        assert {frozenset(pair) for pair in port.calls} == {
            frozenset({"A", "B"}),
            frozenset({"A", "C"}),
            frozenset({"B", "C"}),
        }

    def test_collects_issues_the_port_returns(self) -> None:
        issue = make_issue()
        port = FakeDrugInteractionPort(issue=issue)
        service = DrugInteractionService(
            interaction_port=port, evidence_port=FakeInteractionEvidencePort()
        )
        medications = (make_medication(drug_name="A"), make_medication(drug_name="B"))

        issues = service.detect_known_interactions(medications)

        assert issues == (issue,)

    def test_no_issue_when_port_returns_none(self) -> None:
        service = DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(issue=None),
            evidence_port=FakeInteractionEvidencePort(),
        )
        medications = (make_medication(drug_name="A"), make_medication(drug_name="B"))
        assert service.detect_known_interactions(medications) == ()


class TestReconcileEvidenceLevels:
    def test_backfills_a_missing_evidence_level(self) -> None:
        evidence_port = FakeInteractionEvidencePort(evidence_level=EvidenceLevel.ESTABLISHED)
        service = DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(), evidence_port=evidence_port
        )
        issue = make_issue(evidence_level=None)

        reconciled = service.reconcile_evidence_levels((issue,))

        assert reconciled[0].evidence_level is EvidenceLevel.ESTABLISHED

    def test_overrides_an_ai_reported_evidence_level_with_curated_data(self) -> None:
        evidence_port = FakeInteractionEvidencePort(evidence_level=EvidenceLevel.THEORETICAL)
        service = DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(), evidence_port=evidence_port
        )
        issue = make_issue(evidence_level=EvidenceLevel.ESTABLISHED)

        reconciled = service.reconcile_evidence_levels((issue,))

        assert reconciled[0].evidence_level is EvidenceLevel.THEORETICAL

    def test_leaves_evidence_level_alone_when_the_port_has_no_data(self) -> None:
        evidence_port = FakeInteractionEvidencePort(evidence_level=None)
        service = DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(), evidence_port=evidence_port
        )
        issue = make_issue(evidence_level=EvidenceLevel.PROBABLE)

        reconciled = service.reconcile_evidence_levels((issue,))

        assert reconciled[0].evidence_level is EvidenceLevel.PROBABLE

    def test_ignores_non_drug_drug_categories(self) -> None:
        evidence_port = FakeInteractionEvidencePort(evidence_level=EvidenceLevel.ESTABLISHED)
        service = DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(), evidence_port=evidence_port
        )
        issue = make_issue(
            category=SafetyIssueCategory.CONTRAINDICATION,
            evidence_level=None,
            involved_medications=("Warfarin", "Aspirin"),
        )

        reconciled = service.reconcile_evidence_levels((issue,))

        assert reconciled[0].evidence_level is None
        assert evidence_port.calls == []

    def test_ignores_issues_with_fewer_than_two_involved_medications(self) -> None:
        evidence_port = FakeInteractionEvidencePort(evidence_level=EvidenceLevel.ESTABLISHED)
        service = DrugInteractionService(
            interaction_port=FakeDrugInteractionPort(), evidence_port=evidence_port
        )
        issue = make_issue(evidence_level=None, involved_medications=("Warfarin",))

        reconciled = service.reconcile_evidence_levels((issue,))

        assert reconciled[0].evidence_level is None
