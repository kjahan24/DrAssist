"""Unit tests for `StaticDrugInteractionKnowledgeBase`/
`StaticInteractionEvidenceKnowledgeBase`."""

import pytest

from app.modules.drug_interaction_ai.domain.enums import (
    EvidenceLevel,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.infrastructure.interaction_knowledge.static_drug_interaction_knowledge_base import (  # noqa: E501
    StaticDrugInteractionKnowledgeBase,
    StaticInteractionEvidenceKnowledgeBase,
)

_KNOWN_PAIRS = [
    ("warfarin", "aspirin", SafetySeverity.MAJOR),
    ("warfarin", "ibuprofen", SafetySeverity.MAJOR),
    ("simvastatin", "clarithromycin", SafetySeverity.MAJOR),
    ("sildenafil", "nitroglycerin", SafetySeverity.CONTRAINDICATED),
    ("phenelzine", "sertraline", SafetySeverity.CONTRAINDICATED),
    ("lisinopril", "spironolactone", SafetySeverity.MODERATE),
    ("digoxin", "amiodarone", SafetySeverity.MAJOR),
    ("clopidogrel", "omeprazole", SafetySeverity.MODERATE),
]


class TestCheckPairwiseInteraction:
    def test_returns_none_for_an_unrecognized_pair(self) -> None:
        kb = StaticDrugInteractionKnowledgeBase()
        assert kb.check_pairwise_interaction("acetaminophen", "vitamin c") is None

    @pytest.mark.parametrize("drug_a,drug_b,severity", _KNOWN_PAIRS)
    def test_recognizes_every_known_pair(
        self, drug_a: str, drug_b: str, severity: SafetySeverity
    ) -> None:
        kb = StaticDrugInteractionKnowledgeBase()

        issue = kb.check_pairwise_interaction(drug_a, drug_b)

        assert issue is not None
        assert issue.severity is severity
        assert issue.category is SafetyIssueCategory.DRUG_DRUG_INTERACTION

    def test_is_order_independent(self) -> None:
        kb = StaticDrugInteractionKnowledgeBase()
        forward = kb.check_pairwise_interaction("warfarin", "aspirin")
        backward = kb.check_pairwise_interaction("aspirin", "warfarin")
        assert forward is not None
        assert backward is not None
        assert forward.severity == backward.severity

    def test_is_case_insensitive(self) -> None:
        kb = StaticDrugInteractionKnowledgeBase()
        assert kb.check_pairwise_interaction("WARFARIN", "Aspirin") is not None

    def test_includes_both_drugs_in_involved_medications(self) -> None:
        kb = StaticDrugInteractionKnowledgeBase()
        issue = kb.check_pairwise_interaction("warfarin", "aspirin")
        assert issue is not None
        assert set(issue.involved_medications) == {"warfarin", "aspirin"}

    def test_includes_mechanism_and_clinical_significance(self) -> None:
        kb = StaticDrugInteractionKnowledgeBase()
        issue = kb.check_pairwise_interaction("warfarin", "aspirin")
        assert issue is not None
        assert issue.mechanism is not None
        assert issue.clinical_significance is not None

    def test_a_drug_paired_with_itself_is_not_a_known_interaction(self) -> None:
        kb = StaticDrugInteractionKnowledgeBase()
        assert kb.check_pairwise_interaction("warfarin", "warfarin") is None


class TestClassifyEvidenceLevel:
    def test_returns_none_for_an_unrecognized_pair(self) -> None:
        kb = StaticInteractionEvidenceKnowledgeBase()
        assert kb.classify_evidence_level("acetaminophen", "vitamin c") is None

    @pytest.mark.parametrize("drug_a,drug_b,_severity", _KNOWN_PAIRS)
    def test_recognizes_every_known_pair(
        self, drug_a: str, drug_b: str, _severity: SafetySeverity
    ) -> None:
        kb = StaticInteractionEvidenceKnowledgeBase()
        assert kb.classify_evidence_level(drug_a, drug_b) is not None

    def test_is_order_independent(self) -> None:
        kb = StaticInteractionEvidenceKnowledgeBase()
        forward = kb.classify_evidence_level("digoxin", "amiodarone")
        backward = kb.classify_evidence_level("amiodarone", "digoxin")
        assert forward == backward

    def test_established_pairs_are_graded_established(self) -> None:
        kb = StaticInteractionEvidenceKnowledgeBase()
        assert kb.classify_evidence_level("warfarin", "aspirin") is EvidenceLevel.ESTABLISHED

    def test_suspected_pairs_are_graded_suspected(self) -> None:
        kb = StaticInteractionEvidenceKnowledgeBase()
        assert kb.classify_evidence_level("clopidogrel", "omeprazole") is EvidenceLevel.SUSPECTED
