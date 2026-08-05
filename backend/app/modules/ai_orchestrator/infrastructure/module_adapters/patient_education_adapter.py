"""`PatientEducationWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.PATIENT_EDUCATION`, wrapping
`app.modules.patient_education_ai`'s own public facade — the literal
final step of this task's own WORKFLOW example pipeline. See this
package's own `__init__.py` for the shape every adapter in this package
shares.

The only adapter in this package with **two** prerequisites at once —
that peer module's own `PatientEducationInput` requires both a non-empty
`diagnoses` *and* a non-empty `current_medications`, per its own
"missing diagnosis"/"missing medication list" VALIDATION categories.
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
from app.modules.patient_education_ai.public.dto import (
    PatientEducationInput,
    PatientEducationSetting,
)
from app.modules.patient_education_ai.public.interfaces import PatientEducationAIPort


class PatientEducationWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: PatientEducationAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.PATIENT_EDUCATION

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        reasons: list[str] = []
        if not bundle.diagnoses:
            reasons.append("no diagnoses were provided")
        if not bundle.medication_list:
            reasons.append("no current medications were provided")
        return tuple(reasons)

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        input_dto = PatientEducationInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            education_setting=PatientEducationSetting.ADULT,
            diagnoses=bundle.diagnoses,
            current_medications=bundle.medication_list,
            patient_age=bundle.patient_age,
            clinical_notes=bundle.clinical_notes,
            soap_notes=bundle.soap_notes,
            prescription_ai_output=upstream_summary(context, WorkflowModule.PRESCRIPTION),
            drug_interaction_ai_output=upstream_summary(context, WorkflowModule.DRUG_INTERACTION),
            risk_stratification_ai_output=upstream_summary(
                context, WorkflowModule.RISK_STRATIFICATION
            ),
            laboratory_interpretation=upstream_summary(context, WorkflowModule.LAB_INTERPRETATION),
            radiology_interpretation=upstream_summary(
                context, WorkflowModule.RADIOLOGY_INTERPRETATION
            ),
            pathology_interpretation=upstream_summary(
                context, WorkflowModule.PATHOLOGY_INTERPRETATION
            ),
            medical_reasoning_context=upstream_summary(context, WorkflowModule.MEDICAL_REASONING),
            differential_diagnosis_context=upstream_summary(
                context, WorkflowModule.DIFFERENTIAL_DIAGNOSIS
            ),
            language=bundle.language,
        )
        generated = await self._facade.generate_patient_education(input_dto)
        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.result.raw_text,
            confidence_score=generated.result.confidence_score,
            latency_ms=latency_ms,
        )
