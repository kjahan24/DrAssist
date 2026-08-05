"""Unit tests for `DrugInteractionWorkflowAdapter`."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.drug_interaction_adapter import (
    DrugInteractionWorkflowAdapter,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeDrugInteractionAIPort,
    make_generated_drug_interaction_analysis,
)


class TestDrugInteractionWorkflowAdapter:
    def test_module_is_drug_interaction(self) -> None:
        adapter = DrugInteractionWorkflowAdapter(facade=FakeDrugInteractionAIPort())
        assert adapter.module == WorkflowModule.DRUG_INTERACTION

    def test_check_prerequisites_missing_when_no_medications(self) -> None:
        adapter = DrugInteractionWorkflowAdapter(facade=FakeDrugInteractionAIPort())
        reasons = adapter.check_prerequisites(make_bundle())
        assert reasons == ("no current medications were provided",)

    def test_check_prerequisites_ready_when_medications_present(self) -> None:
        adapter = DrugInteractionWorkflowAdapter(facade=FakeDrugInteractionAIPort())
        bundle = make_bundle(medication_list=("warfarin",))
        assert adapter.check_prerequisites(bundle) == ()

    async def test_execute_builds_one_medication_entry_per_drug_name(self) -> None:
        facade = FakeDrugInteractionAIPort()
        adapter = DrugInteractionWorkflowAdapter(facade=facade)
        bundle = make_bundle(medication_list=("warfarin", "aspirin"))

        await adapter.execute(bundle, {})

        medications = facade.received[0].current_medications
        assert len(medications) == 2
        assert medications[0].drug_name == "warfarin"
        assert medications[1].drug_name == "aspirin"

    async def test_execute_passes_chief_complaint_as_diagnosis(self) -> None:
        facade = FakeDrugInteractionAIPort()
        adapter = DrugInteractionWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            chief_complaint="Atrial fibrillation",
            medication_list=("warfarin",),
            allergies=("latex",),
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.diagnosis == "Atrial fibrillation"
        assert input_dto.allergies == ("latex",)

    async def test_execute_returns_completed_step_result_with_confidence(self) -> None:
        facade = FakeDrugInteractionAIPort(
            generated=make_generated_drug_interaction_analysis(
                raw_text="the drug interaction analysis", confidence_score=0.88
            )
        )
        adapter = DrugInteractionWorkflowAdapter(facade=facade)
        bundle = make_bundle(medication_list=("warfarin",))

        result = await adapter.execute(bundle, {})

        assert result.module == WorkflowModule.DRUG_INTERACTION
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the drug interaction analysis"
        assert result.confidence_score == 0.88

    async def test_execute_passes_patient_age_and_diagnoses_through(self) -> None:
        facade = FakeDrugInteractionAIPort()
        adapter = DrugInteractionWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            medication_list=("warfarin",), patient_age=68, diagnoses=("atrial fibrillation",)
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.patient_age == 68
        assert input_dto.problem_list == ("atrial fibrillation",)
        assert input_dto.medical_conditions == ("atrial fibrillation",)
