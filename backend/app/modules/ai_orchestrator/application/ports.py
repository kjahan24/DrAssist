"""Application-layer ports for the AI Healthcare Orchestrator module,
per this task's explicit "Create ports: HealthcareWorkflowPort,
WorkflowPlannerPort, WorkflowExecutorPort" requirement.

Unlike every prior AI module, only **two** of these three names live
here — `HealthcareWorkflowPort` is this module's own **public** port
instead (`public/interfaces.py`), the same role every prior AI module's
own `<Module>AIPort` plays, just given this task's own literal name
instead of that naming convention, because this task's own GOAL section
is explicit that "It is NOT another AI model. It is the orchestration
layer" — `HealthcareWorkflowPort.execute_workflow`/
`.stream_execute_workflow` are the direct orchestration-layer analogs of
every prior module's own `generate_*`/`stream_generate_*` public
contract. `WorkflowPlannerPort` and `WorkflowExecutorPort` remain here
because they back this module's own **internal** capabilities
(`WorkflowPlannerService`/`WorkflowExecutorService`), the same "ports
back services 1:1" shape `app.modules.patient_education_ai.application
.ports` establishes for its own three explicitly-named ports.

`WorkflowExecutorPort` has **twelve** concrete implementations, one per
`WorkflowModule` (`infrastructure/module_adapters/*.py`) — a genuine
departure from the "one port, one concrete adapter" shape every prior
AI module's own knowledge-base port establishes for itself, because this
port's whole purpose is adapting *many* heterogeneous peer modules
behind *one* uniform seam; `WorkflowExecutorService` holds the resulting
`Mapping[WorkflowModule, WorkflowExecutorPort]` registry and dispatches
by `.module`.

Extended with the operationally-necessary
`WorkflowOrchestrationAuditLoggerPort` (AUDIT), prefixed distinctly from
the two explicitly-named ports above, the same "named ports plus the
operationally-necessary rest, prefixed to avoid collision" precedent
every prior AI module's own `application/ports.py` establishes for
itself. No `CostEstimatorPort` this time — this module makes no direct
LLM call of its own (see `domain/value_objects.py
::WorkflowExecutionSession`'s own docstring for why), so there is no
token cost of its own to estimate.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from uuid import UUID

from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition,
    WorkflowExecutionInput,
    WorkflowExecutionSession,
    WorkflowStepResult,
)


class WorkflowPlannerPort(ABC):
    """This task's own explicitly-named deterministic planning seam:
    given an already-validated `WorkflowDefinition` (validation is
    `WorkflowValidationService`'s own, separate concern — see that
    service's own docstring for why planning assumes an already-valid
    graph), computes one valid topological execution order over its
    steps' `depends_on` edges.
    """

    @abstractmethod
    def compute_execution_order(
        self, definition: WorkflowDefinition
    ) -> tuple[WorkflowModule, ...]: ...


class WorkflowExecutorPort(ABC):
    """This task's own explicitly-named deterministic (per invocation)
    step-execution seam — one concrete implementation per orchestrated
    `WorkflowModule` (see this file's own module docstring for why there
    are twelve of these, unlike every prior AI module's own knowledge-
    base port).

    - `module` identifies which `WorkflowModule` this adapter handles,
      so `WorkflowExecutorService` can build its own dispatch registry
      by iterating a list of adapters rather than hardcoding twelve
      names.
    - `check_prerequisites` returns a tuple of human-readable missing-
      prerequisite reasons (empty tuple = this step's own peer module
      has enough information in `bundle` to run); never raises.
    - `execute` performs the real translation-and-delegation: turns
      `bundle` (plus already-completed upstream steps' own `context`
      text) into this adapter's own peer module's strongly-typed input,
      calls that peer's own public facade, and returns a
      `WorkflowStepResult`. Only ever called after `check_prerequisites`
      has returned an empty tuple for this same `bundle` — an adapter
      does not need to re-check what its own caller already checked.
    """

    @property
    @abstractmethod
    def module(self) -> WorkflowModule: ...

    @abstractmethod
    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]: ...

    @abstractmethod
    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult: ...


class WorkflowOrchestrationAuditLoggerPort(ABC):
    @abstractmethod
    async def log_execution(
        self, session: WorkflowExecutionSession, *, organization_id: UUID, patient_id: UUID
    ) -> None: ...

    @abstractmethod
    async def log_failure(
        self,
        *,
        execution_id: UUID,
        organization_id: UUID,
        patient_id: UUID,
        stage: str,
        error_code: str,
        message: str,
    ) -> None: ...
