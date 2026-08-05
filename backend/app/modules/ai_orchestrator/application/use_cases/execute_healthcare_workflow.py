"""`ExecuteHealthcareWorkflowUseCase` — orchestrates the pipeline this
task specifies:

    (input already validated by
     `WorkflowExecutionInput.__post_init__`/`WorkflowDefinition
     .__post_init__`)
    -> `WorkflowValidationService.validate_graph` (invalid graph/
       circular dependency/duplicate execution — always strict, see
       that service's own docstring)
    -> `WorkflowPlannerService.plan` (a valid topological execution
       order over the graph's `depends_on` edges)
    -> for each module in that order, `WorkflowExecutorService
       .execute_step` (prerequisite/dependency-output checking,
       skipping, retry, timeout, and failure isolation are all that
       service's own concern — see its own docstring). Every completed
       step's own `summary` is folded into `context`, so later steps'
       own adapters see earlier steps' own output text as
       `existing_ai_outputs`-shaped context (the same "each later
       peer-module call sees earlier steps' output as plain context
       text" design this task's own literal WORKFLOW example pipeline
       depicts).
    -> `WorkflowResultComposerService.compose` (this task's own nine-
       item OUTPUT specification)
    -> audit logging (`WorkflowExecutionSession`, per this task's own
       AUDIT section)
    -> return `GeneratedWorkflowExecution`

Only this module's **own** graph-validation exceptions are caught and
turned into an audit `log_failure` entry — a failure *within* a single
step never reaches this use case as an exception at all (it is already
converted into a `WorkflowStepResult` with `status=FAILED` by
`WorkflowExecutorService`, per this task's own "module failure
isolation" requirement), so there is nothing else for this use case's
own `execute` to catch.

`stream_execute` is this module's own "progressive workflow events"
entry point (this task's own STREAMING section) — it bypasses
`WorkflowResultComposerService`/audit logging entirely, the same
"streaming bypasses the parse/validate/audit pipeline" scope every
prior AI module's own generator documents for its own token-level
streaming, applied here at step granularity instead (see `domain
/value_objects.py::WorkflowProgressEvent`'s own docstring for why).
"""

from collections.abc import AsyncIterator
from time import perf_counter
from uuid import uuid4

from app.modules.ai_orchestrator.application.dto import (
    GeneratedWorkflowExecution,
    WorkflowCancellationToken,
    WorkflowExecutionRequest,
)
from app.modules.ai_orchestrator.application.ports import WorkflowOrchestrationAuditLoggerPort
from app.modules.ai_orchestrator.application.services.workflow_executor_service import (
    WorkflowExecutorService,
)
from app.modules.ai_orchestrator.application.services.workflow_planner_service import (
    WorkflowPlannerService,
)
from app.modules.ai_orchestrator.application.services.workflow_result_composer_service import (
    WorkflowResultComposerService,
)
from app.modules.ai_orchestrator.application.services.workflow_validation_service import (
    WorkflowValidationService,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.exceptions import (
    CircularDependencyError,
    DuplicateModuleExecutionError,
    InvalidWorkflowGraphError,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition,
    WorkflowExecutionInput,
    WorkflowExecutionSession,
    WorkflowProgressEvent,
    WorkflowStepResult,
)
from app.shared.application.use_case import UseCase

_GRAPH_ERRORS = (
    DuplicateModuleExecutionError,
    InvalidWorkflowGraphError,
    CircularDependencyError,
)


class ExecuteHealthcareWorkflowUseCase(
    UseCase[WorkflowExecutionRequest, GeneratedWorkflowExecution]
):
    def __init__(
        self,
        *,
        validation_service: WorkflowValidationService,
        planner_service: WorkflowPlannerService,
        executor_service: WorkflowExecutorService,
        composer_service: WorkflowResultComposerService,
        audit_logger: WorkflowOrchestrationAuditLoggerPort,
    ) -> None:
        self._validation_service = validation_service
        self._planner_service = planner_service
        self._executor_service = executor_service
        self._composer_service = composer_service
        self._audit_logger = audit_logger

    async def execute(self, input_dto: WorkflowExecutionRequest) -> GeneratedWorkflowExecution:
        definition = input_dto.definition
        bundle = input_dto.bundle
        cancellation_token = input_dto.cancellation_token
        execution_id = uuid4()

        try:
            self._validation_service.validate_graph(definition)
        except _GRAPH_ERRORS as exc:
            await self._audit_logger.log_failure(
                execution_id=execution_id,
                organization_id=bundle.organization_id,
                patient_id=bundle.patient_id,
                stage="validate_graph",
                error_code=type(exc).__name__,
                message=str(exc),
            )
            raise

        execution_order = self._planner_service.plan(definition)
        steps_by_module = {step.module: step for step in definition.steps}

        context: dict[WorkflowModule, str] = dict(bundle.existing_ai_outputs)
        completed_results: dict[WorkflowModule, WorkflowStepResult] = {}
        step_results: list[WorkflowStepResult] = []
        module_timings: dict[WorkflowModule, float] = {}
        retry_count = 0
        failure_count = 0

        start = perf_counter()
        for module in execution_order:
            step = steps_by_module[module]
            result = await self._executor_service.execute_step(
                step,
                bundle,
                context,
                completed_results,
                cancellation_token=cancellation_token,
            )
            step_results.append(result)
            completed_results[module] = result
            module_timings[module] = result.latency_ms
            if result.attempt_count > 1:
                retry_count += result.attempt_count - 1
            if result.status is WorkflowStepStatus.FAILED:
                failure_count += 1
            if result.status is WorkflowStepStatus.COMPLETED and result.summary is not None:
                context[module] = result.summary
        total_execution_time_ms = (perf_counter() - start) * 1000

        workflow_result = self._composer_service.compose(
            definition, tuple(step_results), total_execution_time_ms
        )
        session = WorkflowExecutionSession(
            execution_id=execution_id,
            workflow_name=definition.name,
            execution_order=execution_order,
            total_latency_ms=total_execution_time_ms,
            module_timings=module_timings,
            failure_count=failure_count,
            retry_count=retry_count,
            status=workflow_result.status,
        )
        await self._audit_logger.log_execution(
            session, organization_id=bundle.organization_id, patient_id=bundle.patient_id
        )
        return GeneratedWorkflowExecution(result=workflow_result, session=session)

    async def stream_execute(
        self,
        definition: WorkflowDefinition,
        bundle: WorkflowExecutionInput,
        cancellation_token: WorkflowCancellationToken | None = None,
    ) -> AsyncIterator[WorkflowProgressEvent]:
        self._validation_service.validate_graph(definition)
        execution_order = self._planner_service.plan(definition)
        steps_by_module = {step.module: step for step in definition.steps}

        context: dict[WorkflowModule, str] = dict(bundle.existing_ai_outputs)
        completed_results: dict[WorkflowModule, WorkflowStepResult] = {}

        for sequence, module in enumerate(execution_order):
            step = steps_by_module[module]
            yield WorkflowProgressEvent(
                module=module, status=WorkflowStepStatus.RUNNING, sequence=sequence
            )
            result = await self._executor_service.execute_step(
                step, bundle, context, completed_results, cancellation_token=cancellation_token
            )
            completed_results[module] = result
            if result.status is WorkflowStepStatus.COMPLETED and result.summary is not None:
                context[module] = result.summary
            is_final = sequence == len(execution_order) - 1
            yield WorkflowProgressEvent(
                module=module, status=result.status, sequence=sequence, is_final=is_final
            )
