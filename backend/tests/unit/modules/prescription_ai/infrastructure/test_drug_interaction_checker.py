"""Unit tests for `StaticDrugInteractionChecker`."""

from app.modules.prescription_ai.domain.enums import SafetyFindingCategory
from app.modules.prescription_ai.infrastructure.interactions.drug_interaction_checker import (
    StaticDrugInteractionChecker,
)


class TestCheckInteractions:
    def test_flags_a_known_interacting_pair(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_interactions(("warfarin", "aspirin"))

        assert len(findings) == 1
        assert findings[0].category is SafetyFindingCategory.DRUG_INTERACTION
        assert set(findings[0].affected_medications) == {"warfarin", "aspirin"}

    def test_does_not_flag_an_unrelated_pair(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_interactions(("amoxicillin", "acetaminophen"))

        assert findings == ()

    def test_is_case_insensitive(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_interactions(("Warfarin", "ASPIRIN"))

        assert len(findings) == 1

    def test_a_single_medication_produces_no_findings(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_interactions(("warfarin",))

        assert findings == ()

    def test_checks_all_pairs_among_three_or_more_medications(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_interactions(("warfarin", "aspirin", "amoxicillin"))

        assert len(findings) == 1
        assert set(findings[0].affected_medications) == {"warfarin", "aspirin"}

    def test_does_not_duplicate_a_pair_appearing_via_repeated_names(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_interactions(("warfarin", "aspirin", "warfarin"))

        assert len(findings) == 1


class TestCheckAllergyConflicts:
    def test_flags_a_cross_reactive_medication(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_allergy_conflicts(("amoxicillin",), ("penicillin",))

        assert len(findings) == 1
        assert findings[0].category is SafetyFindingCategory.ALLERGY_CONFLICT
        assert findings[0].affected_medications == ("amoxicillin",)

    def test_does_not_flag_a_non_cross_reactive_medication(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_allergy_conflicts(("acetaminophen",), ("penicillin",))

        assert findings == ()

    def test_no_allergies_produces_no_findings(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_allergy_conflicts(("amoxicillin",), ())

        assert findings == ()

    def test_is_case_insensitive(self) -> None:
        checker = StaticDrugInteractionChecker()

        findings = checker.check_allergy_conflicts(("Amoxicillin",), ("PENICILLIN",))

        assert len(findings) == 1
