"""`PathologyInterpretationWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.PATHOLOGY_INTERPRETATION`, wrapping
`app.modules.pathology_interpretation_ai`'s own public facade. See this
package's own `__init__.py` for the shape every adapter in this package
shares.

`examination_type` always resolves to
`PathologyExaminationType.HISTOPATHOLOGY` — unlike radiology, this peer
module's own examination-type vocabulary has no catch-all "general"
member, so histopathology (the broadest, most common textual pathology
report type) is this adapter's own documented default when this
orchestrator was not told a more specific one.
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
from app.modules.pathology_interpretation_ai.public.dto import (
    PathologyExaminationType,
    PathologyInterpretationInput,
    PathologySetting,
)
from app.modules.pathology_interpretation_ai.public.interfaces import (
    PathologyInterpretationAIPort,
)

_MIN_REPORT_LENGTH = 10


class PathologyInterpretationWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: PathologyInterpretationAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.PATHOLOGY_INTERPRETATION

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        if not bundle.pathology_findings:
            return ("no pathology findings were provided",)
        report_text = "; ".join(bundle.pathology_findings).strip()
        if len(report_text) < _MIN_REPORT_LENGTH or not any(char.isalpha() for char in report_text):
            return ("pathology findings are too short to interpret as a report",)
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        input_dto = PathologyInterpretationInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            report_text="; ".join(bundle.pathology_findings),
            examination_type=PathologyExaminationType.HISTOPATHOLOGY,
            pathology_setting=PathologySetting.OUTPATIENT,
            language=bundle.language,
            visit_id=bundle.visit_id,
            patient_age=bundle.patient_age,
            clinical_notes=bundle.clinical_notes,
            soap_notes=bundle.soap_notes,
            laboratory_interpretation=upstream_summary(context, WorkflowModule.LAB_INTERPRETATION),
            radiology_interpretation=upstream_summary(
                context, WorkflowModule.RADIOLOGY_INTERPRETATION
            ),
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
