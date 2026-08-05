"""Unit tests for `ClinicalNoteWorkflowAdapter`."""

from uuid import uuid4

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.infrastructure.module_adapters.clinical_note_adapter import (
    ClinicalNoteWorkflowAdapter,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle
from tests.unit.modules.ai_orchestrator.infrastructure.module_adapters._peer_fakes import (
    FakeClinicalNoteAIPort,
    make_generated_clinical_note,
)


class TestClinicalNoteWorkflowAdapter:
    def test_module_is_clinical_note(self) -> None:
        adapter = ClinicalNoteWorkflowAdapter(facade=FakeClinicalNoteAIPort())
        assert adapter.module == WorkflowModule.CLINICAL_NOTE

    def test_check_prerequisites_always_ready(self) -> None:
        adapter = ClinicalNoteWorkflowAdapter(facade=FakeClinicalNoteAIPort())
        assert adapter.check_prerequisites(make_bundle()) == ()

    async def test_execute_builds_encounter_input_from_bundle(self) -> None:
        facade = FakeClinicalNoteAIPort()
        adapter = ClinicalNoteWorkflowAdapter(facade=facade)
        bundle = make_bundle(
            chief_complaint="Shortness of breath",
            language="es",
            symptoms=("cough", "fever"),
            medication_list=("aspirin",),
            allergies=("penicillin",),
            diagnoses=("asthma",),
            encounter_notes=("patient appears anxious",),
        )

        await adapter.execute(bundle, {})

        assert len(facade.received) == 1
        encounter = facade.received[0]
        assert encounter.organization_id == bundle.organization_id
        assert encounter.patient_id == bundle.patient_id
        assert encounter.chief_complaint == "Shortness of breath"
        assert encounter.language == "es"
        assert encounter.symptoms == ("cough", "fever")
        assert encounter.medications == ("aspirin",)
        assert encounter.allergies == ("penicillin",)
        assert encounter.diagnoses == ("asthma",)
        assert encounter.encounter_context == "patient appears anxious"

    async def test_execute_returns_completed_step_result(self) -> None:
        facade = FakeClinicalNoteAIPort(
            generated=make_generated_clinical_note(raw_text="the clinical note")
        )
        adapter = ClinicalNoteWorkflowAdapter(facade=facade)

        result = await adapter.execute(make_bundle(), {})

        assert result.module == WorkflowModule.CLINICAL_NOTE
        assert result.status == WorkflowStepStatus.COMPLETED
        assert result.summary == "the clinical note"
        assert result.confidence_score is None
        assert result.latency_ms >= 0.0

    async def test_execute_with_no_encounter_notes_leaves_context_none(self) -> None:
        facade = FakeClinicalNoteAIPort()
        adapter = ClinicalNoteWorkflowAdapter(facade=facade)

        await adapter.execute(make_bundle(), {})

        assert facade.received[0].encounter_context is None

    async def test_execute_passes_visit_id_through(self) -> None:
        facade = FakeClinicalNoteAIPort()
        adapter = ClinicalNoteWorkflowAdapter(facade=facade)
        visit_id = uuid4()

        await adapter.execute(make_bundle(visit_id=visit_id), {})

        assert facade.received[0].visit_id == visit_id

    async def test_execute_passes_organization_and_patient_id_through(self) -> None:
        facade = FakeClinicalNoteAIPort()
        adapter = ClinicalNoteWorkflowAdapter(facade=facade)
        bundle = make_bundle()

        await adapter.execute(bundle, {})

        assert facade.received[0].organization_id == bundle.organization_id
        assert facade.received[0].patient_id == bundle.patient_id
