"""`MedicalReasoningWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.MEDICAL_REASONING`, wrapping
`app.modules.medical_reasoning_ai`'s own public facade. See this
package's own `__init__.py` for the shape every adapter in this package
shares, and `clinical_note_adapter.py`'s own docstring for why
`check_prerequisites` always returns `()`.

`confidence_score` is the arithmetic mean of that peer module's own
three separate confidence fields (`clinical_confidence`,
`diagnostic_confidence`, `therapeutic_confidence` —
`MedicalReasoningResult` carries no single unified `confidence_score`
of its own, unlike every other diagnostic/interpretation peer module),
skipping whichever of the three are `None`; `None` only when all three
are.
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
from app.modules.medical_reasoning_ai.public.dto import MedicalReasoningInput, ReasoningSetting
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort


def _average_confidence(*scores: float | None) -> float | None:
    present = [score for score in scores if score is not None]
    if not present:
        return None
    return sum(present) / len(present)


class MedicalReasoningWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: MedicalReasoningAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.MEDICAL_REASONING

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        icd10_summary = upstream_summary(context, WorkflowModule.ICD10_CODING)
        clinical_note = upstream_summary(context, WorkflowModule.CLINICAL_NOTE)
        soap_note = upstream_summary(context, WorkflowModule.SOAP_NOTE)
        evidence = MedicalReasoningInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            chief_complaint=bundle.chief_complaint,
            reasoning_setting=ReasoningSetting.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            symptoms=bundle.symptoms,
            vitals=bundle.vital_signs,
            allergies=bundle.allergies,
            medications=bundle.medication_list,
            medical_conditions=bundle.diagnoses,
            laboratory_results=bundle.laboratory_findings,
            imaging_summary=upstream_summary(context, WorkflowModule.RADIOLOGY_INTERPRETATION)
            or upstream_summary(context, WorkflowModule.PATHOLOGY_INTERPRETATION)
            or join_or_none(bundle.radiology_findings + bundle.pathology_findings),
            clinical_notes=bundle.clinical_notes + ((clinical_note,) if clinical_note else ()),
            soap_notes=bundle.soap_notes + ((soap_note,) if soap_note else ()),
            diagnoses=bundle.diagnoses,
            icd10_suggestions=(icd10_summary,) if icd10_summary is not None else (),
        )
        generated = await self._facade.generate_reasoning(evidence)
        latency_ms = (perf_counter() - start) * 1000
        result = generated.result
        confidence_score = _average_confidence(
            result.clinical_confidence, result.diagnostic_confidence, result.therapeutic_confidence
        )
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=result.raw_text,
            confidence_score=confidence_score,
            latency_ms=latency_ms,
        )
