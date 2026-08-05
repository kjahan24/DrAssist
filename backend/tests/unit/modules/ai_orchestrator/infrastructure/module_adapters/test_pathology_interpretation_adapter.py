"""Unit tests for `PathologyInterpretationWorkflowAdapter`."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.pathology_interpretation_adapter import (  # noqa: E501
    PathologyInterpretationWorkflowAdapter,
)
from app.modules.pathology_interpretation_ai.public.dto import PathologyExaminationType
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakePathologyInterpretationAIPort,
    make_generated_pathology_interpretation,
)


class TestPathologyInterpretationWorkflowAdapter:
    def test_module_is_pathology_interpretation(self) -> None:
        adapter = PathologyInterpretationWorkflowAdapter(facade=FakePathologyInterpretationAIPort())
        assert adapter.module == WorkflowModule.PATHOLOGY_INTERPRETATION

    def test_check_prerequisites_missing_when_no_findings(self) -> None:
        adapter = PathologyInterpretationWorkflowAdapter(facade=FakePathologyInterpretationAIPort())
        reasons = adapter.check_prerequisites(make_bundle())
        assert reasons == ("no pathology findings were provided",)

    def test_check_prerequisites_missing_when_too_short(self) -> None:
        adapter = PathologyInterpretationWorkflowAdapter(facade=FakePathologyInterpretationAIPort())
        bundle = make_bundle(pathology_findings=("ok",))
        reasons = adapter.check_prerequisites(bundle)
        assert reasons == ("pathology findings are too short to interpret as a report",)

    def test_check_prerequisites_ready_when_findings_are_a_real_report(self) -> None:
        adapter = PathologyInterpretationWorkflowAdapter(facade=FakePathologyInterpretationAIPort())
        bundle = make_bundle(pathology_findings=("benign reactive lymph node hyperplasia",))
        assert adapter.check_prerequisites(bundle) == ()

    async def test_execute_joins_findings_into_report_text_with_histopathology_type(self) -> None:
        facade = FakePathologyInterpretationAIPort()
        adapter = PathologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(pathology_findings=("benign tissue", "no malignancy"))

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.report_text == "benign tissue; no malignancy"
        assert input_dto.examination_type == PathologyExaminationType.HISTOPATHOLOGY

    async def test_execute_chains_upstream_lab_radiology_and_medical_reasoning(self) -> None:
        facade = FakePathologyInterpretationAIPort()
        adapter = PathologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(pathology_findings=("benign tissue",))
        context = {
            WorkflowModule.LAB_INTERPRETATION: "upstream lab interpretation",
            WorkflowModule.RADIOLOGY_INTERPRETATION: "upstream radiology interpretation",
            WorkflowModule.MEDICAL_REASONING: "upstream medical reasoning",
        }

        await adapter.execute(bundle, context)

        input_dto = facade.received[0]
        assert input_dto.laboratory_interpretation == "upstream lab interpretation"
        assert input_dto.radiology_interpretation == "upstream radiology interpretation"
        assert input_dto.medical_reasoning_context == "upstream medical reasoning"

    async def test_execute_returns_completed_step_result_with_confidence(self) -> None:
        facade = FakePathologyInterpretationAIPort(
            generated=make_generated_pathology_interpretation(
                raw_text="the pathology interpretation", confidence_score=0.55
            )
        )
        adapter = PathologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(pathology_findings=("benign tissue",))

        result = await adapter.execute(bundle, {})

        assert result.module == WorkflowModule.PATHOLOGY_INTERPRETATION
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the pathology interpretation"
        assert result.confidence_score == 0.55

    async def test_execute_passes_patient_age_and_clinical_notes_through(self) -> None:
        facade = FakePathologyInterpretationAIPort()
        adapter = PathologyInterpretationWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            pathology_findings=("benign tissue",),
            patient_age=62,
            clinical_notes=("prior note",),
            soap_notes=("prior soap",),
        )

        await adapter.execute(bundle, {})

        input_dto = facade.received[0]
        assert input_dto.patient_age == 62
        assert input_dto.clinical_notes == ("prior note",)
        assert input_dto.soap_notes == ("prior soap",)
