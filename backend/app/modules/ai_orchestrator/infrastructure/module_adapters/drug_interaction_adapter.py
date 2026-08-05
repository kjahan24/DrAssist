"""`DrugInteractionWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.DRUG_INTERACTION`, wrapping
`app.modules.drug_interaction_ai`'s own public facade. See this
package's own `__init__.py` for the shape every adapter in this package
shares.

Each plain drug-name string in `bundle.medication_list` becomes one
`MedicationEntry(drug_name=...)` — that peer module's own value object
needs only `drug_name` to be non-blank, so no other field is fabricated.
"""

from collections.abc import Mapping
from time import perf_counter

from app.modules.ai_orchestrator.application.ports import WorkflowExecutorPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput,
    WorkflowStepResult,
)
from app.modules.drug_interaction_ai.public.dto import (
    DrugInteractionAnalysisInput,
    DrugInteractionSetting,
    MedicationEntry,
)
from app.modules.drug_interaction_ai.public.interfaces import DrugInteractionAIPort


class DrugInteractionWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: DrugInteractionAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.DRUG_INTERACTION

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        if not bundle.medication_list:
            return ("no current medications were provided",)
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        input_dto = DrugInteractionAnalysisInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            medication_setting=DrugInteractionSetting.OUTPATIENT,
            current_medications=tuple(
                MedicationEntry(drug_name=drug_name) for drug_name in bundle.medication_list
            ),
            diagnosis=bundle.chief_complaint,
            problem_list=bundle.diagnoses,
            allergies=bundle.allergies,
            medical_conditions=bundle.diagnoses,
            patient_age=bundle.patient_age,
            recent_lab_values=bundle.laboratory_findings,
            language=bundle.language,
        )
        generated = await self._facade.analyze_medication_safety(input_dto)
        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.result.raw_text,
            confidence_score=generated.result.confidence_score,
            latency_ms=latency_ms,
        )
