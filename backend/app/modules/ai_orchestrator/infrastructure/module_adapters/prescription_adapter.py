"""`PrescriptionWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.PRESCRIPTION`, wrapping
`app.modules.prescription_ai`'s own public facade. See this package's
own `__init__.py` for the shape every adapter in this package shares,
and `clinical_note_adapter.py`'s own docstring for why
`check_prerequisites` always returns `()`.
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
from app.modules.prescription_ai.public.dto import (
    PrescribingSetting,
    PrescriptionContextInput,
)
from app.modules.prescription_ai.public.interfaces import PrescriptionAIPort


class PrescriptionWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: PrescriptionAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.PRESCRIPTION

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        icd10_summary = upstream_summary(context, WorkflowModule.ICD10_CODING)
        prescription_context = PrescriptionContextInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            chief_complaint=bundle.chief_complaint,
            prescribing_setting=PrescribingSetting.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            symptoms=bundle.symptoms,
            vitals=bundle.vital_signs,
            clinical_note=upstream_summary(context, WorkflowModule.CLINICAL_NOTE),
            soap_note=upstream_summary(context, WorkflowModule.SOAP_NOTE),
            icd10_suggestions=(icd10_summary,) if icd10_summary is not None else (),
            existing_medications=bundle.medication_list,
            allergies=bundle.allergies,
            medical_conditions=bundle.diagnoses,
            laboratory_results=bundle.laboratory_findings,
            patient_age=bundle.patient_age,
        )
        generated = await self._facade.generate_suggestion(prescription_context)
        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.suggestions.raw_text,
            confidence_score=None,
            latency_ms=latency_ms,
        )
