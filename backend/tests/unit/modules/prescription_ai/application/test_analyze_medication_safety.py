"""Unit tests for `AnalyzeMedicationSafetyUseCase`."""

from app.modules.prescription_ai.application.dto import MedicationSafetyAnalysisInput
from app.modules.prescription_ai.application.services.medication_safety_analysis_service import (
    MedicationSafetyAnalysisService,
)
from app.modules.prescription_ai.application.use_cases.analyze_medication_safety import (
    AnalyzeMedicationSafetyUseCase,
)
from app.modules.prescription_ai.domain.enums import SafetyFindingCategory, SafetySeverity
from app.modules.prescription_ai.domain.value_objects import MedicationSafetyFinding
from tests.unit.modules.prescription_ai.application.fakes import (
    FakeDrugInteractionPort,
    FakeMedicationKnowledgePort,
    make_medication,
)


class TestAnalyzeMedicationSafetyUseCase:
    async def test_delegates_to_the_safety_service(self) -> None:
        finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.DRUG_INTERACTION,
            severity=SafetySeverity.HIGH,
            description="Interaction found",
        )
        service = MedicationSafetyAnalysisService(
            drug_interaction=FakeDrugInteractionPort(interaction_findings=(finding,)),
            knowledge=FakeMedicationKnowledgePort(),
        )
        use_case = AnalyzeMedicationSafetyUseCase(safety_service=service)

        result = await use_case.execute(
            MedicationSafetyAnalysisInput(medications=(make_medication(),))
        )

        assert finding in result

    async def test_passes_existing_medications_and_allergies_through(self) -> None:
        drug_interaction = FakeDrugInteractionPort()
        service = MedicationSafetyAnalysisService(
            drug_interaction=drug_interaction, knowledge=FakeMedicationKnowledgePort()
        )
        use_case = AnalyzeMedicationSafetyUseCase(safety_service=service)

        await use_case.execute(
            MedicationSafetyAnalysisInput(
                medications=(make_medication(generic_name="ibuprofen"),),
                existing_medications=("warfarin",),
                allergies=("penicillin",),
            )
        )

        assert "warfarin" in drug_interaction.interaction_calls[0]
        assert drug_interaction.allergy_calls[0][1] == ("penicillin",)
