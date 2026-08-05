"""Unit tests for `PrescriptionWorkflowAdapter`."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.prescription_adapter import (
    PrescriptionWorkflowAdapter,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakePrescriptionAIPort,
    make_generated_prescription_suggestions,
)


class TestPrescriptionWorkflowAdapter:
    def test_module_is_prescription(self) -> None:
        adapter = PrescriptionWorkflowAdapter(facade=FakePrescriptionAIPort())
        assert adapter.module == WorkflowModule.PRESCRIPTION

    def test_check_prerequisites_always_ready(self) -> None:
        adapter = PrescriptionWorkflowAdapter(facade=FakePrescriptionAIPort())
        assert adapter.check_prerequisites(make_bundle()) == ()

    async def test_execute_with_no_upstream_icd10_gives_empty_suggestions_tuple(self) -> None:
        facade = FakePrescriptionAIPort()
        adapter = PrescriptionWorkflowAdapter(facade=facade)

        await adapter.execute(make_bundle(medication_list=("metformin",), allergies=("sulfa",)), {})

        prescription_context = facade.received[0]
        assert prescription_context.icd10_suggestions == ()
        assert prescription_context.existing_medications == ("metformin",)
        assert prescription_context.allergies == ("sulfa",)

    async def test_execute_chains_upstream_clinical_note_soap_note_and_icd10(self) -> None:
        facade = FakePrescriptionAIPort()
        adapter = PrescriptionWorkflowAdapter(facade=facade)
        context = {
            WorkflowModule.CLINICAL_NOTE: "upstream clinical note",
            WorkflowModule.SOAP_NOTE: "upstream soap note",
            WorkflowModule.ICD10_CODING: "upstream icd10 codes",
        }

        await adapter.execute(make_bundle(), context)

        prescription_context = facade.received[0]
        assert prescription_context.clinical_note == "upstream clinical note"
        assert prescription_context.soap_note == "upstream soap note"
        assert prescription_context.icd10_suggestions == ("upstream icd10 codes",)

    async def test_execute_returns_completed_step_result(self) -> None:
        facade = FakePrescriptionAIPort(
            generated=make_generated_prescription_suggestions(raw_text="the prescriptions")
        )
        adapter = PrescriptionWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.module == WorkflowModule.PRESCRIPTION
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the prescriptions"
        assert result.confidence_score is None

    async def test_execute_passes_patient_age_and_laboratory_results_through(self) -> None:
        facade = FakePrescriptionAIPort()
        adapter = PrescriptionWorkflowAdapter(facade=facade)
        bundle = make_bundle(patient_age=70, laboratory_findings=("creatinine 1.4",))

        await adapter.execute(bundle, {})

        prescription_context = facade.received[0]
        assert prescription_context.patient_age == 70
        assert prescription_context.laboratory_results == ("creatinine 1.4",)
