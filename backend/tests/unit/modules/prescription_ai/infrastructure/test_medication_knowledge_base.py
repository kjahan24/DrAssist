"""Unit tests for `StaticMedicationKnowledgeBase`."""

from app.modules.prescription_ai.infrastructure.knowledge.medication_knowledge_base import (
    StaticMedicationKnowledgeBase,
)


class TestIsKnownMedication:
    def test_returns_true_for_a_known_medication(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.is_known_medication("ibuprofen") is True

    def test_returns_false_for_an_unrecognized_medication(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.is_known_medication("not-a-real-drug") is False

    def test_is_case_insensitive(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.is_known_medication("Ibuprofen") is True


class TestLookupTherapeuticClass:
    def test_returns_the_class_for_a_known_medication(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.lookup_therapeutic_class("ibuprofen") == "NSAID"

    def test_returns_none_for_an_unrecognized_medication(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.lookup_therapeutic_class("not-a-real-drug") is None

    def test_is_case_insensitive(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.lookup_therapeutic_class("IBUPROFEN") == "NSAID"

    def test_strips_surrounding_whitespace(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.lookup_therapeutic_class("  ibuprofen  ") == "NSAID"

    def test_naproxen_shares_ibuprofens_therapeutic_class(self) -> None:
        knowledge = StaticMedicationKnowledgeBase()
        assert knowledge.lookup_therapeutic_class(
            "ibuprofen"
        ) == knowledge.lookup_therapeutic_class("naproxen")
