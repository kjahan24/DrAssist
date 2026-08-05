"""`DifferentialDiagnosisWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.DIFFERENTIAL_DIAGNOSIS`, wrapping
`app.modules.differential_diagnosis_ai`'s own public facade. See this
package's own `__init__.py` for the shape every adapter in this package
shares, and `clinical_note_adapter.py`'s own docstring for why
`check_prerequisites` always returns `()`.

`confidence_score` is read off the top-ranked candidate
(`DifferentialDiagnosisResult.candidates[0]`) rather than the result
itself — that peer module's own `confidence_score` is a **per-candidate**
field (`DifferentialDiagnosisCandidate.confidence_score`), not a
top-level one, and `most_likely_diagnosis` is that peer module's own
documented reading of "the candidate that matters most" once ranked.
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
from app.modules.differential_diagnosis_ai.public.dto import (
    ClinicalSetting,
    DifferentialDiagnosisInput,
)
from app.modules.differential_diagnosis_ai.public.interfaces import DifferentialDiagnosisAIPort


class DifferentialDiagnosisWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: DifferentialDiagnosisAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.DIFFERENTIAL_DIAGNOSIS

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        icd10_summary = upstream_summary(context, WorkflowModule.ICD10_CODING)
        evidence = DifferentialDiagnosisInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            chief_complaint=bundle.chief_complaint,
            clinical_setting=ClinicalSetting.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            symptoms=bundle.symptoms,
            laboratory_results=bundle.laboratory_findings,
            imaging_summary=upstream_summary(context, WorkflowModule.RADIOLOGY_INTERPRETATION)
            or join_or_none(bundle.radiology_findings),
            clinical_note=upstream_summary(context, WorkflowModule.CLINICAL_NOTE),
            soap_note=upstream_summary(context, WorkflowModule.SOAP_NOTE),
            icd10_suggestions=(icd10_summary,) if icd10_summary is not None else (),
            allergies=bundle.allergies,
            medical_conditions=bundle.diagnoses,
            patient_age=bundle.patient_age,
        )
        generated = await self._facade.generate_differential_diagnosis(evidence)
        latency_ms = (perf_counter() - start) * 1000
        candidates = generated.result.candidates
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.result.raw_text,
            confidence_score=candidates[0].confidence_score if candidates else None,
            latency_ms=latency_ms,
        )
