"""Unit tests for `ICD10CodingWorkflowAdapter`."""

from uuid import uuid4

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.icd10_coding_adapter import (
    ICD10CodingWorkflowAdapter,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeICD10AIPort,
    make_generated_icd10_suggestions,
)


class TestICD10CodingWorkflowAdapter:
    def test_module_is_icd10_coding(self) -> None:
        adapter = ICD10CodingWorkflowAdapter(facade=FakeICD10AIPort())
        assert adapter.module == WorkflowModule.ICD10_CODING

    def test_check_prerequisites_always_ready(self) -> None:
        adapter = ICD10CodingWorkflowAdapter(facade=FakeICD10AIPort())
        assert adapter.check_prerequisites(make_bundle()) == ()

    async def test_execute_with_no_upstream_notes_passes_none(self) -> None:
        facade = FakeICD10AIPort()
        adapter = ICD10CodingWorkflowAdapter(facade=facade)

        await adapter.execute(make_bundle(diagnoses=("hypertension",), patient_age=60), {})

        coding_input = facade.received[0]
        assert coding_input.clinical_note is None
        assert coding_input.soap_note is None
        assert coding_input.existing_diagnoses == ("hypertension",)
        assert coding_input.patient_age == 60

    async def test_execute_chains_upstream_clinical_note_and_soap_note(self) -> None:
        facade = FakeICD10AIPort()
        adapter = ICD10CodingWorkflowAdapter(facade=facade)
        context = {
            WorkflowModule.CLINICAL_NOTE: "upstream clinical note",
            WorkflowModule.SOAP_NOTE: "upstream soap note",
        }

        await adapter.execute(make_bundle(), context)

        coding_input = facade.received[0]
        assert coding_input.clinical_note == "upstream clinical note"
        assert coding_input.soap_note == "upstream soap note"

    async def test_execute_returns_completed_step_result(self) -> None:
        facade = FakeICD10AIPort(
            generated=make_generated_icd10_suggestions(raw_text="the icd10 suggestions")
        )
        adapter = ICD10CodingWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.module == WorkflowModule.ICD10_CODING
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the icd10 suggestions"
        assert result.confidence_score is None

    async def test_execute_passes_visit_id_and_language_through(self) -> None:
        facade = FakeICD10AIPort()
        adapter = ICD10CodingWorkflowAdapter(facade=facade)
        visit_id = uuid4()

        await adapter.execute(make_bundle(visit_id=visit_id, language="fr"), {})

        coding_input = facade.received[0]
        assert coding_input.visit_id == visit_id
        assert coding_input.language == "fr"
