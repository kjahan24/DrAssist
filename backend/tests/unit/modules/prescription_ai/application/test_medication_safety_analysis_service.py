"""Unit tests for `MedicationSafetyAnalysisService` — the deterministic
half of this task's own "MEDICATION SAFETY" requirement."""

from app.modules.prescription_ai.application.services.medication_safety_analysis_service import (
    MedicationSafetyAnalysisService,
)
from app.modules.prescription_ai.domain.enums import SafetyFindingCategory, SafetySeverity
from app.modules.prescription_ai.domain.value_objects import MedicationSafetyFinding
from tests.unit.modules.prescription_ai.application.fakes import (
    FakeDrugInteractionPort,
    FakeMedicationKnowledgePort,
    make_medication,
)


class TestMedicationSafetyAnalysisServiceDelegation:
    async def test_includes_drug_interaction_findings(self) -> None:
        finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.DRUG_INTERACTION,
            severity=SafetySeverity.HIGH,
            description="Interaction detected",
        )
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(interaction_findings=(finding,)),
            knowledge=FakeMedicationKnowledgePort(),
        )

        findings = service.analyze(medications=(make_medication(),))

        assert finding in findings

    async def test_includes_allergy_conflict_findings(self) -> None:
        finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.ALLERGY_CONFLICT,
            severity=SafetySeverity.HIGH,
            description="Allergy conflict detected",
        )
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(allergy_findings=(finding,)),
            knowledge=FakeMedicationKnowledgePort(),
        )

        findings = service.analyze(medications=(make_medication(),), allergies=("penicillin",))

        assert finding in findings

    def test_folds_existing_medications_into_the_checked_name_pool(self) -> None:
        drug_interaction = FakeDrugInteractionPort()
        service = MedicationSafetyAnalysisService(
            drug_interaction=drug_interaction, knowledge=FakeMedicationKnowledgePort()
        )

        service.analyze(
            medications=(make_medication(generic_name="ibuprofen"),),
            existing_medications=("warfarin",),
        )

        assert drug_interaction.interaction_calls[0] == ("ibuprofen", "warfarin")


class TestMedicationSafetyAnalysisServiceDuplicateTherapy:
    def test_flags_two_medications_sharing_a_therapeutic_class(self) -> None:
        knowledge = FakeMedicationKnowledgePort(
            therapeutic_classes={"ibuprofen": "NSAID", "naproxen": "NSAID"}
        )
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(), knowledge=knowledge
        )

        findings = service.analyze(
            medications=(
                make_medication(generic_name="ibuprofen"),
                make_medication(generic_name="naproxen"),
            )
        )

        duplicate_findings = [
            f for f in findings if f.category is SafetyFindingCategory.DUPLICATE_THERAPY
        ]
        assert len(duplicate_findings) == 1
        assert set(duplicate_findings[0].affected_medications) == {"ibuprofen", "naproxen"}

    def test_does_not_flag_medications_in_different_therapeutic_classes(self) -> None:
        knowledge = FakeMedicationKnowledgePort(
            therapeutic_classes={"ibuprofen": "NSAID", "amoxicillin": "Penicillin antibiotic"}
        )
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(), knowledge=knowledge
        )

        findings = service.analyze(
            medications=(
                make_medication(generic_name="ibuprofen"),
                make_medication(generic_name="amoxicillin"),
            )
        )

        assert not any(f.category is SafetyFindingCategory.DUPLICATE_THERAPY for f in findings)

    def test_does_not_flag_a_medication_appearing_only_once(self) -> None:
        knowledge = FakeMedicationKnowledgePort(therapeutic_classes={"ibuprofen": "NSAID"})
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(), knowledge=knowledge
        )

        findings = service.analyze(medications=(make_medication(generic_name="ibuprofen"),))

        assert not any(f.category is SafetyFindingCategory.DUPLICATE_THERAPY for f in findings)

    def test_medications_with_unknown_therapeutic_class_are_not_flagged(self) -> None:
        knowledge = FakeMedicationKnowledgePort(therapeutic_classes={})
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(), knowledge=knowledge
        )

        findings = service.analyze(
            medications=(
                make_medication(generic_name="obscure-drug-a"),
                make_medication(generic_name="obscure-drug-b"),
            )
        )

        assert not any(f.category is SafetyFindingCategory.DUPLICATE_THERAPY for f in findings)

    def test_the_same_medication_name_appearing_twice_is_not_flagged_as_duplicate_therapy(
        self,
    ) -> None:
        """Regression guard: an exact-name repeat (e.g. the same drug
        also listed in `existing_medications`) is not a *therapeutic*
        duplicate — it is literally the same medication, not two
        different drugs sharing a class."""
        knowledge = FakeMedicationKnowledgePort(therapeutic_classes={"ibuprofen": "NSAID"})
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(), knowledge=knowledge
        )

        findings = service.analyze(
            medications=(make_medication(generic_name="ibuprofen"),),
            existing_medications=("ibuprofen",),
        )

        assert not any(f.category is SafetyFindingCategory.DUPLICATE_THERAPY for f in findings)
