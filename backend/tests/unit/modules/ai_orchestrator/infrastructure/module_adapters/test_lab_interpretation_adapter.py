"""Unit tests for `LabInterpretationWorkflowAdapter`."""

from uuid import uuid4

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.lab_interpretation_adapter import (
    LabInterpretationWorkflowAdapter,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeLabInterpretationAIPort,
    make_generated_lab_interpretation,
)


class TestLabInterpretationWorkflowAdapter:
    def test_module_is_lab_interpretation(self) -> None:
        adapter = LabInterpretationWorkflowAdapter(facade=FakeLabInterpretationAIPort())
        assert adapter.module == WorkflowModule.LAB_INTERPRETATION

    def test_check_prerequisites_missing_when_no_findings(self) -> None:
        adapter = LabInterpretationWorkflowAdapter(facade=FakeLabInterpretationAIPort())
        reasons = adapter.check_prerequisites(make_bundle())
        assert reasons == ("no laboratory findings were provided",)

    def test_check_prerequisites_ready_when_findings_present(self) -> None:
        adapter = LabInterpretationWorkflowAdapter(facade=FakeLabInterpretationAIPort())
        bundle = make_bundle(laboratory_findings=("glucose 250",))
        assert adapter.check_prerequisites(bundle) == ()

    async def test_execute_synthesizes_lab_values_from_free_text_findings(self) -> None:
        facade = FakeLabInterpretationAIPort()
        adapter = LabInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(laboratory_findings=("glucose 250", "wbc 15k"))

        await adapter.execute(bundle, {})

        lab_values = facade.received[0].lab_values
        assert len(lab_values) == 2
        assert lab_values[0].test_name == "Finding 1"
        assert lab_values[0].value == "glucose 250"
        assert lab_values[1].test_name == "Finding 2"
        assert lab_values[1].value == "wbc 15k"

    async def test_execute_passes_bundle_context_fields(self) -> None:
        facade = FakeLabInterpretationAIPort()
        adapter = LabInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            laboratory_findings=("glucose 250",),
            diagnoses=("diabetes",),
            allergies=("iodine",),
            medication_list=("insulin",),
            patient_age=55,
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.medical_conditions == ("diabetes",)
        assert input_dto.allergies == ("iodine",)
        assert input_dto.medications == ("insulin",)
        assert input_dto.patient_age == 55

    async def test_execute_returns_completed_step_result_with_confidence(self) -> None:
        facade = FakeLabInterpretationAIPort(
            generated=make_generated_lab_interpretation(
                raw_text="the lab interpretation", confidence_score=0.77
            )
        )
        adapter = LabInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(laboratory_findings=("glucose 250",))

        result = await adapter.execute(bundle, {})

        assert result.module == WorkflowModule.LAB_INTERPRETATION
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the lab interpretation"
        assert result.confidence_score == 0.77

    async def test_execute_passes_visit_id_and_clinical_notes_through(self) -> None:
        facade = FakeLabInterpretationAIPort()
        adapter = LabInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            laboratory_findings=("glucose 250",),
            visit_id=uuid4(),
            clinical_notes=("prior note",),
            soap_notes=("prior soap",),
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.visit_id == bundle.visit_id
        assert input_dto.clinical_notes == ("prior note",)
        assert input_dto.soap_notes == ("prior soap",)
