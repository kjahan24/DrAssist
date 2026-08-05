"""`HealthcareOrchestratorFacade` — the one concrete implementation of
`HealthcareWorkflowPort`. Constructed by `app.modules.ai_orchestrator
.container.get_healthcare_orchestrator_facade`.

`stream_execute_workflow` delegates directly to
`ExecuteHealthcareWorkflowUseCase.stream_execute` (not a second use
case) — this task names exactly one use case,
`ExecuteHealthcareWorkflowUseCase`, which itself exposes both the
audited, composed `execute` path and the bypassed, progressive
`stream_execute` path (see that use case's own module docstring for
why), the same "no separate object wraps streaming" choice every prior
AI module's own facade makes for its own generator.
"""

from collections.abc import AsyncIterator

from app.modules.ai_orchestrator.application.use_cases.execute_healthcare_workflow import (
    ExecuteHealthcareWorkflowUseCase,
)
from app.modules.ai_orchestrator.public.dto import (
    GeneratedWorkflowExecution,
    WorkflowExecutionRequest,
    WorkflowProgressEvent,
)
from app.modules.ai_orchestrator.public.interfaces import HealthcareWorkflowPort


class HealthcareOrchestratorFacade(HealthcareWorkflowPort):
    def __init__(self, *, execute_use_case: ExecuteHealthcareWorkflowUseCase) -> None:
        self._execute_use_case = execute_use_case

    async def execute_workflow(
        self, request: WorkflowExecutionRequest
    ) -> GeneratedWorkflowExecution:
        return await self._execute_use_case.execute(request)

    def stream_execute_workflow(
        self, request: WorkflowExecutionRequest
    ) -> AsyncIterator[WorkflowProgressEvent]:
        return self._execute_use_case.stream_execute(
            request.definition, request.bundle, request.cancellation_token
        )
