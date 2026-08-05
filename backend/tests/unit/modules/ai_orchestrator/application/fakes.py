"""In-memory test doubles for the AI Healthcare Orchestrator module's
application-layer ports — per `docs/backend-architecture
/12_testing_architecture.md` ("fakes over mocks as the default").
"""

import asyncio
from collections.abc import Mapping
from uuid import UUID, uuid4

from app.modules.ai_orchestrator.application.ports import (
    WorkflowExecutorPort,
    WorkflowOrchestrationAuditLoggerPort,
    WorkflowPlannerPort,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition,
    WorkflowExecutionInput,
    WorkflowExecutionSession,
    WorkflowStepDefinition,
    WorkflowStepResult,
)


def make_bundle(**overrides: object) -> WorkflowExecutionInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
    }
    defaults.update(overrides)
    return WorkflowExecutionInput(**defaults)  # type: ignore[arg-type]


def make_step(module: WorkflowModule, **overrides: object) -> WorkflowStepDefinition:
    defaults: dict[str, object] = {"module": module}
    defaults.update(overrides)
    return WorkflowStepDefinition(**defaults)  # type: ignore[arg-type]


def make_definition(
    *steps: WorkflowStepDefinition, name: str = "test-workflow"
) -> WorkflowDefinition:
    return WorkflowDefinition(name=name, steps=steps or (make_step(WorkflowModule.CLINICAL_NOTE),))


def make_step_result(module: WorkflowModule, **overrides: object) -> WorkflowStepResult:
    defaults: dict[str, object] = {
        "module": module,
        "status": WorkflowStepStatus.COMPLETED,
        "summary": f"{module.value} summary",
    }
    defaults.update(overrides)
    return WorkflowStepResult(**defaults)  # type: ignore[arg-type]


class FakeWorkflowExecutorAdapter(WorkflowExecutorPort):
    def __init__(
        self,
        *,
        module: WorkflowModule,
        missing_reasons: tuple[str, ...] = (),
        result: WorkflowStepResult | None = None,
        error: Exception | None = None,
        fail_times: int = 0,
        delay_seconds: float = 0.0,
    ) -> None:
        self._module = module
        self._missing_reasons = missing_reasons
        self._result = result or make_step_result(module)
        self._error = error
        self._fail_times = fail_times
        self._delay_seconds = delay_seconds
        self._call_count = 0
        self.execute_calls: list[WorkflowExecutionInput] = []
        self.context_calls: list[dict[WorkflowModule, str]] = []
        self.prerequisite_calls: list[WorkflowExecutionInput] = []

    @property
    def module(self) -> WorkflowModule:
        return self._module

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        self.prerequisite_calls.append(bundle)
        return self._missing_reasons

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        self._call_count += 1
        self.execute_calls.append(bundle)
        self.context_calls.append(dict(context))
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        if self._fail_times and self._call_count <= self._fail_times:
            raise self._error or RuntimeError("simulated failure")
        if self._error is not None and not self._fail_times:
            raise self._error
        return self._result


class FakeWorkflowPlannerPort(WorkflowPlannerPort):
    def __init__(self, *, order: tuple[WorkflowModule, ...] | None = None) -> None:
        self._order = order
        self.calls: list[WorkflowDefinition] = []

    def compute_execution_order(self, definition: WorkflowDefinition) -> tuple[WorkflowModule, ...]:
        self.calls.append(definition)
        if self._order is not None:
            return self._order
        return tuple(step.module for step in definition.steps)


class FakeWorkflowOrchestrationAuditLoggerPort(WorkflowOrchestrationAuditLoggerPort):
    def __init__(self) -> None:
        self.executions: list[WorkflowExecutionSession] = []
        self.failures: list[dict[str, object]] = []

    async def log_execution(
        self, session: WorkflowExecutionSession, *, organization_id: UUID, patient_id: UUID
    ) -> None:
        self.executions.append(session)

    async def log_failure(
        self,
        *,
        execution_id: UUID,
        organization_id: UUID,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None:
        self.failures.append(
            {
                "execution_id": execution_id,
                "organization_id": organization_id,
                "patient_id": patient_id,
                "stage": stage,
                "error_code": error_code,
                "message": message,
            }
        )
