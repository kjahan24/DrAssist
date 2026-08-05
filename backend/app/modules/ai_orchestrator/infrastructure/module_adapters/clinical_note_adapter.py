"""`ClinicalNoteWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.CLINICAL_NOTE`, wrapping
`app.modules.clinical_note_ai`'s own public facade. See this package's
own `__init__.py` for the shape every adapter in this package shares.

`check_prerequisites` always returns `()` — `bundle.chief_complaint` is
already guaranteed non-blank by `WorkflowExecutionInput.__post_init__`,
so this adapter (and every other "chief-complaint-family" adapter —
`soap_note`/`icd10_coding`/`prescription`/`differential_diagnosis`/
`medical_reasoning`) has no additional prerequisite of its own beyond
what already always holds by the time a `WorkflowExecutionInput` exists
at all.
"""

from collections.abc import Mapping
from time import perf_counter

from app.modules.ai_orchestrator.application.ports import WorkflowExecutorPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput,
    WorkflowStepResult,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters._common import join_or_none
from app.modules.clinical_note_ai.public.dto import ClinicalEncounterInput, NoteStyle
from app.modules.clinical_note_ai.public.interfaces import ClinicalNoteAIPort


class ClinicalNoteWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: ClinicalNoteAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.CLINICAL_NOTE

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        encounter = ClinicalEncounterInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            chief_complaint=bundle.chief_complaint,
            note_style=NoteStyle.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            symptoms=bundle.symptoms,
            medications=bundle.medication_list,
            allergies=bundle.allergies,
            vitals=bundle.vital_signs,
            diagnoses=bundle.diagnoses,
            encounter_context=join_or_none(bundle.encounter_notes),
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
