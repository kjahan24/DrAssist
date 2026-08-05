"""`LabInterpretationWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.LAB_INTERPRETATION`, wrapping
`app.modules.lab_interpretation_ai`'s own public facade. See this
package's own `__init__.py` for the shape every adapter in this package
shares.

`bundle.laboratory_findings` is free text (this task's own SUPPORTED
INPUT section names "Laboratory" as a flat item, not already-parsed
named lab values), while `LabInterpretationInput.lab_values` needs
`tuple[LabValue, ...]` — each finding becomes one synthetically-named
`LabValue` (`test_name="Finding N"`, `value=<the finding text>`), the
one place in this package's own translation logic that manufactures a
field name rather than reading one straight off `bundle`; a real
structured integration would come from a future caller supplying
already-parsed `LabValue`s of its own instead.
"""

from collections.abc import Mapping
from time import perf_counter

from app.modules.ai_orchestrator.application.ports import WorkflowExecutorPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput,
    WorkflowStepResult,
)
from app.modules.lab_interpretation_ai.public.dto import (
    LabInterpretationInput,
    LabInterpretationSetting,
    LabValue,
)
from app.modules.lab_interpretation_ai.public.interfaces import LabInterpretationAIPort


class LabInterpretationWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: LabInterpretationAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.LAB_INTERPRETATION

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        if not bundle.laboratory_findings:
            return ("no laboratory findings were provided",)
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        lab_values = tuple(
            LabValue(test_name=f"Finding {index + 1}", value=finding)
            for index, finding in enumerate(bundle.laboratory_findings)
        )
        input_dto = LabInterpretationInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            lab_values=lab_values,
            lab_setting=LabInterpretationSetting.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            patient_age=bundle.patient_age,
            medical_conditions=bundle.diagnoses,
            allergies=bundle.allergies,
            medications=bundle.medication_list,
            clinical_notes=bundle.clinical_notes,
            soap_notes=bundle.soap_notes,
        )
        generated = await self._facade.generate_interpretation(input_dto)
        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.result.raw_text,
            confidence_score=generated.result.confidence_score,
            latency_ms=latency_ms,
        )
