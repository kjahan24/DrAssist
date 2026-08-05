"""`RadiologyInterpretationWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.RADIOLOGY_INTERPRETATION`, wrapping
`app.modules.radiology_interpretation_ai`'s own public facade. See this
package's own `__init__.py` for the shape every adapter in this package
shares.

`examination_type` always resolves to `RadiologyExaminationType.GENERAL`
— that peer module's own catch-all member for "a textual radiology
report whose specific modality this orchestrator was not told" (this
task's own generic `WorkflowExecutionInput` has no
per-examination-type field of its own).
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
from app.modules.radiology_interpretation_ai.public.dto import (
    RadiologyExaminationType,
    RadiologyInterpretationInput,
    RadiologySetting,
)
from app.modules.radiology_interpretation_ai.public.interfaces import (
    RadiologyInterpretationAIPort,
)

_MIN_REPORT_LENGTH = 10


class RadiologyInterpretationWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: RadiologyInterpretationAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.RADIOLOGY_INTERPRETATION

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        if not bundle.radiology_findings:
            return ("no radiology findings were provided",)
        report_text = "; ".join(bundle.radiology_findings).strip()
        if len(report_text) < _MIN_REPORT_LENGTH or not any(char.isalpha() for char in report_text):
            return ("radiology findings are too short to interpret as a report",)
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        input_dto = RadiologyInterpretationInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            report_text="; ".join(bundle.radiology_findings),
            examination_type=RadiologyExaminationType.GENERAL,
            radiology_setting=RadiologySetting.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            patient_age=bundle.patient_age,
            clinical_notes=bundle.clinical_notes,
            soap_notes=bundle.soap_notes,
            laboratory_interpretation=upstream_summary(context, WorkflowModule.LAB_INTERPRETATION),
            medical_reasoning_context=upstream_summary(context, WorkflowModule.MEDICAL_REASONING),
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
