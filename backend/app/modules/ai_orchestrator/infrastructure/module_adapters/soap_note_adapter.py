"""`SOAPNoteWorkflowAdapter` — the `WorkflowExecutorPort` implementation
for `WorkflowModule.SOAP_NOTE`, wrapping `app.modules.soap_note_ai`'s
own public facade. See this package's own `__init__.py` for the shape
every adapter in this package shares, and `clinical_note_adapter.py`'s
own docstring for why `check_prerequisites` always returns `()`.

`encounter_context` prefers `WorkflowModule.CLINICAL_NOTE`'s own already-
completed output over `bundle.encounter_notes` — the literal first two
steps of this task's own WORKFLOW example pipeline ("Clinical Note ->
SOAP") — falling back to the caller-supplied encounter notes only when
no clinical note step ran first (this workflow started at SOAP, or the
clinical-note step was skipped/failed).
"""

from collections.abc import Mapping
from time import perf_counter

from app.modules.ai_orchestrator.application.ports import WorkflowExecutorPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput,
    WorkflowStepResult,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters._common import (
    join_or_none,
    upstream_summary,
)
from app.modules.soap_note_ai.public.dto import SOAPEncounterInput, SOAPStyle
from app.modules.soap_note_ai.public.interfaces import SOAPNoteAIPort


class SOAPNoteWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: SOAPNoteAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.SOAP_NOTE

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        encounter_context = upstream_summary(context, WorkflowModule.CLINICAL_NOTE) or join_or_none(
            bundle.encounter_notes
        )
        encounter = SOAPEncounterInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            chief_complaint=bundle.chief_complaint,
            soap_style=SOAPStyle.STANDARD,
            language=bundle.language,
            visit_id=bundle.visit_id,
            symptoms=bundle.symptoms,
            vitals=bundle.vital_signs,
            medications=bundle.medication_list,
            allergies=bundle.allergies,
            diagnoses=bundle.diagnoses,
            encounter_context=encounter_context,
            patient_age=bundle.patient_age,
        )
        generated = await self._facade.generate_note(encounter)
        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.note.raw_text,
            confidence_score=None,
            latency_ms=latency_ms,
        )
