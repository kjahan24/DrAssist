"""`ICD10CodingWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.ICD10_CODING`, wrapping
`app.modules.icd10_ai`'s own public facade. See this package's own
`__init__.py` for the shape every adapter in this package shares, and
`clinical_note_adapter.py`'s own docstring for why `check_prerequisites`
always returns `()`.
"""

from collections.abc import Mapping
from time import perf_counter

from app.modules.ai_orchestrator.application.ports import WorkflowExecutorPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput,
    WorkflowStepResult,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters._common import upstream_summary
from app.modules.icd10_ai.public.dto import CodingSetting, ICD10CodingInput
from app.modules.icd10_ai.public.interfaces import ICD10AIPort


class ICD10CodingWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: ICD10AIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.ICD10_CODING

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        coding_input = ICD10CodingInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            chief_complaint=bundle.chief_complaint,
            coding_setting=CodingSetting.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            symptoms=bundle.symptoms,
            clinical_note=upstream_summary(context, WorkflowModule.CLINICAL_NOTE),
            soap_note=upstream_summary(context, WorkflowModule.SOAP_NOTE),
            existing_diagnoses=bundle.diagnoses,
            patient_age=bundle.patient_age,
        )
        generated = await self._facade.generate_suggestions(coding_input)
        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.suggestions.raw_text,
            confidence_score=None,
            latency_ms=latency_ms,
        )
