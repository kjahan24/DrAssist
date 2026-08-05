"""Unit tests for `RadiologyInterpretationWorkflowAdapter`."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.radiology_interpretation_adapter import (  # noqa: E501
    RadiologyInterpretationWorkflowAdapter,
)
from app.modules.radiology_interpretation_ai.public.dto import RadiologyExaminationType
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeRadiologyInterpretationAIPort,
    make_generated_radiology_interpretation,
)


class TestRadiologyInterpretationWorkflowAdapter:
    def test_module_is_radiology_interpretation(self) -> None:
        adapter = RadiologyInterpretationWorkflowAdapter(facade=FakeRadiologyInterpretationAIPort())
        assert adapter.module == WorkflowModule.RADIOLOGY_INTERPRETATION

    def test_check_prerequisites_missing_when_no_findings(self) -> None:
        adapter = RadiologyInterpretationWorkflowAdapter(facade=FakeRadiologyInterpretationAIPort())
        reasons = adapter.check_prerequisites(make_bundle())
        assert reasons == ("no radiology findings were provided",)

    def test_check_prerequisites_missing_when_too_short(self) -> None:
        adapter = RadiologyInterpretationWorkflowAdapter(facade=FakeRadiologyInterpretationAIPort())
        bundle = make_bundle(radiology_findings=("ok",))
        reasons = adapter.check_prerequisites(bundle)
        assert reasons == ("radiology findings are too short to interpret as a report",)

    def test_check_prerequisites_ready_when_findings_are_a_real_report(self) -> None:
        adapter = RadiologyInterpretationWorkflowAdapter(facade=FakeRadiologyInterpretationAIPort())
        bundle = make_bundle(radiology_findings=("no acute cardiopulmonary abnormality",))
        assert adapter.check_prerequisites(bundle) == ()

    async def test_execute_joins_findings_into_report_text_with_general_examination_type(
        self,
    ) -> None:
        facade = FakeRadiologyInterpretationAIPort()
        adapter = RadiologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(radiology_findings=("clear lungs", "no effusion"))

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.report_text == "clear lungs; no effusion"
        assert input_dto.examination_type == RadiologyExaminationType.GENERAL

    async def test_execute_chains_upstream_lab_and_medical_reasoning(self) -> None:
        facade = FakeRadiologyInterpretationAIPort()
        adapter = RadiologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(radiology_findings=("clear lungs",))
        context = {
            WorkflowModule.LAB_INTERPRETATION: "upstream lab interpretation",
            WorkflowModule.MEDICAL_REASONING: "upstream medical reasoning",
        }

        await adapter.execute(bundle, context)

        input_dto = facade.received[0]
        assert input_dto.laboratory_interpretation == "upstream lab interpretation"
        assert input_dto.medical_reasoning_context == "upstream medical reasoning"

    async def test_execute_returns_completed_step_result_with_confidence(self) -> None:
        facade = FakeRadiologyInterpretationAIPort(
            generated=make_generated_radiology_interpretation(
                raw_text="the radiology interpretation", confidence_score=0.66
            )
        )
        adapter = RadiologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(radiology_findings=("clear lungs",))

        result = await adapter.execute(bundle, {})

        assert result.module == WorkflowModule.RADIOLOGY_INTERPRETATION
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the radiology interpretation"
        assert result.confidence_score == 0.66

    async def test_execute_passes_patient_age_and_clinical_notes_through(self) -> None:
        facade = FakeRadiologyInterpretationAIPort()
        adapter = RadiologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            radiology_findings=("clear lungs",),
            patient_age=48,
            clinical_notes=("prior note",),
            soap_notes=("prior soap",),
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.patient_age == 48
        assert input_dto.clinical_notes == ("prior note",)
        assert input_dto.soap_notes == ("prior soap",)
