"""`WorkflowResultComposerService` — this task's own explicitly-named
APPLICATION service: pure aggregation logic (no port — the same "not
every named service needs a port" precedent
`app.modules.risk_stratification_ai.application.services
.risk_explanation_service.RiskExplanationService` establishes for its
own module) that turns one execution's raw `WorkflowStepResult`s into
this task's own nine-item OUTPUT specification
(`domain/value_objects.py::WorkflowResult`).

`status` determination, in order:

1. Any `CANCELLED` step -> `WorkflowStatus.CANCELLED`.
2. No step reached `COMPLETED` -> `WorkflowStatus.FAILED`.
3. A `FAILED` step whose own `WorkflowStepDefinition.required` is `True`
   -> `WorkflowStatus.PARTIALLY_COMPLETED` (per this task's own "Support
   partial execution" requirement — a required failure downgrades the
   outcome but never discards the steps that *did* succeed).
4. Otherwise -> `WorkflowStatus.COMPLETED` — this covers both "every
   step completed" and "some optional steps were skipped/failed but
   every required one completed", since a skip is never itself a
   failure (see `WorkflowExecutorService`'s own docstring).

`confidence_summary` is a simple arithmetic mean of every completed
step's own `confidence_score` (`None` when no completed step reported
one) — deliberately **not** computed via `MedicalReasoningAIPort
.score_confidence`, unlike every prior AI module's own confidence-
scoring enrichment step: that port's own signature
(`ai_reported, supporting_count, contradicting_count,
missing_information_count`) models blending *one* generation's own
self-reported confidence against evidence counts *within that same
generation* — it has no natural reading as "average several already-
final confidence scores from twelve unrelated generations", and forcing
that fit would be exactly the same "fabricated integration" failure
mode every prior AI module's own container.py documents rejecting for
its own, differently-shaped case. See `container.py`'s own module
docstring for this investigated-and-declined reasoning in full.
"""

from app.modules.ai_orchestrator.domain.enums import WorkflowStatus, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStepResult,
)


class WorkflowResultComposerService:
    def compose(
        self,
        definition: WorkflowDefinition,
        step_results: tuple[WorkflowStepResult, ...],
        total_execution_time_ms: float,
    ) -> WorkflowResult:
        executed = tuple(r.module for r in step_results if r.status is WorkflowStepStatus.COMPLETED)
        skipped = tuple(
            r.module
            for r in step_results
            if r.status in (WorkflowStepStatus.SKIPPED, WorkflowStepStatus.CANCELLED)
        )
        failed_results = tuple(r for r in step_results if r.status is WorkflowStepStatus.FAILED)

        errors = tuple(
            f"{r.module.value}: {r.error_message}" for r in failed_results if r.error_message
        )
        warnings = tuple(
            f"{r.module.value}: {r.skipped_reason}"
            for r in step_results
            if r.status in (WorkflowStepStatus.SKIPPED, WorkflowStepStatus.CANCELLED)
            and r.skipped_reason
        )

        status = self._determine_status(definition, step_results, executed, failed_results)
        clinical_summary = " ".join(
            r.summary
            for r in step_results
            if r.status is WorkflowStepStatus.COMPLETED and r.summary
        )
        confidence_summary = self._average_confidence(step_results)
        workflow_summary = self._build_workflow_summary(
            definition, executed, failed_results, skipped, total_execution_time_ms
        )

        return WorkflowResult(
            workflow_name=definition.name,
            status=status,
            workflow_summary=workflow_summary,
            executed_modules=executed,
            skipped_modules=skipped,
            step_results=step_results,
            total_execution_time_ms=total_execution_time_ms,
            errors=errors,
            warnings=warnings,
            clinical_summary=clinical_summary,
            confidence_summary=confidence_summary,
        )

    def _determine_status(
        self,
        definition: WorkflowDefinition,
        step_results: tuple[WorkflowStepResult, ...],
        executed: tuple[object, ...],
        failed_results: tuple[WorkflowStepResult, ...],
    ) -> WorkflowStatus:
        if any(r.status is WorkflowStepStatus.CANCELLED for r in step_results):
            return WorkflowStatus.CANCELLED
        if not executed:
            return WorkflowStatus.FAILED
        required_modules = {step.module for step in definition.steps if step.required}
        if any(r.module in required_modules for r in failed_results):
            return WorkflowStatus.PARTIALLY_COMPLETED
        return WorkflowStatus.COMPLETED

    def _average_confidence(self, step_results: tuple[WorkflowStepResult, ...]) -> float | None:
        scores = [
            r.confidence_score
            for r in step_results
            if r.status is WorkflowStepStatus.COMPLETED and r.confidence_score is not None
        ]
        if not scores:
            return None
        return sum(scores) / len(scores)

    def _build_workflow_summary(
        self,
        definition: WorkflowDefinition,
        executed: tuple[object, ...],
        failed_results: tuple[WorkflowStepResult, ...],
        skipped: tuple[object, ...],
        total_execution_time_ms: float,
    ) -> str:
        summary = (
            f"Executed {len(executed)} of {len(definition.steps)} module(s) "
            f"in {total_execution_time_ms:.0f}ms"
        )
        if failed_results:
            summary += f"; {len(failed_results)} failed"
        if skipped:
            summary += f"; {len(skipped)} skipped"
        return summary
