"""Unit tests for `SOAPNoteWorkflowAdapter`."""

from uuid import uuid4

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.soap_note_adapter import (
    SOAPNoteWorkflowAdapter,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeSOAPNoteAIPort,
    make_generated_soap_note,
)


class TestSOAPNoteWorkflowAdapter:
    def test_module_is_soap_note(self) -> None:
        adapter = SOAPNoteWorkflowAdapter(facade=FakeSOAPNoteAIPort())
        assert adapter.module == WorkflowModule.SOAP_NOTE

    def test_check_prerequisites_always_ready(self) -> None:
        adapter = SOAPNoteWorkflowAdapter(facade=FakeSOAPNoteAIPort())
        assert adapter.check_prerequisites(make_bundle()) == ()

    async def test_execute_falls_back_to_encounter_notes_when_no_upstream_clinical_note(
        self,
    ) -> None:
        facade = FakeSOAPNoteAIPort()
        adapter = SOAPNoteWorkflowAdapter(facade=facade)
        bundle = make_bundle(encounter_notes=("patient reports fatigue",), patient_age=45)

        await adapter.execute(bundle, {})

        encounter = facade.received[0]
        assert encounter.encounter_context == "patient reports fatigue"
        assert encounter.patient_age == 45

    async def test_execute_prefers_upstream_clinical_note_over_encounter_notes(self) -> None:
        facade = FakeSOAPNoteAIPort()
        adapter = SOAPNoteWorkflowAdapter(facade=facade)
        bundle = make_bundle(encounter_notes=("fallback text",))
        context = {WorkflowModule.CLINICAL_NOTE: "upstream clinical note text"}

        await adapter.execute(bundle, context)

        assert facade.received[0].encounter_context == "upstream clinical note text"

    async def test_execute_returns_completed_step_result(self) -> None:
        facade = FakeSOAPNoteAIPort(generated=make_generated_soap_note(raw_text="the soap note"))
        adapter = SOAPNoteWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.module == WorkflowModule.SOAP_NOTE
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the soap note"
        assert result.confidence_score is None

    async def test_execute_passes_visit_id_and_ids_through(self) -> None:
        facade = FakeSOAPNoteAIPort()
        adapter = SOAPNoteWorkflowAdapter(facade=facade)
        visit_id = uuid4()
        bundle = make_bundle(visit_id=visit_id)

        await adapter.execute(bundle, {})

        encounter = facade.received[0]
        assert encounter.visit_id == visit_id
        assert encounter.organization_id == bundle.organization_id
        assert encounter.patient_id == bundle.patient_id
