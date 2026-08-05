"""Data Transfer Objects for the AI Healthcare Orchestrator module's
application layer — use-case input/output shapes that aren't already a
domain value object in their own right."""

from dataclasses import dataclass, field

from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition,
    WorkflowExecutionInput,
    WorkflowExecutionSession,
    WorkflowResult,
)


@dataclass(frozen=True, slots=True)
class GeneratedWorkflowExecution:
    """`ExecuteHealthcareWorkflowUseCase`'s output — bundles the
    composed result with its `WorkflowExecutionSession`, the same
    "result + session" shape every prior AI module's own use-case DTO
    establishes for itself."""

    result: WorkflowResult
    session: WorkflowExecutionSession


@dataclass(slots=True)
class WorkflowCancellationToken:
    """A caller-held, mutable cancellation flag, per this task's own
    "Support cancellation" requirement. Deliberately **not** a frozen
    domain value object — cancellation is inherently a mutable,
    cross-cutting concern the caller flips from *outside* the use case's
    own call stack (e.g. in response to an HTTP client disconnecting),
    the same reason `asyncio.Event`/`threading.Event` are themselves
    mutable rather than immutable value types. `WorkflowExecutorService`
    checks `.is_cancelled` before starting each step, never mid-step
    (this module makes no direct LLM call it could interrupt partway
    through — interrupting a peer module's own in-flight AI Foundation
    call is that peer module's own concern, out of scope here)."""

    _cancelled: bool = field(default=False, init=False)

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True


@dataclass(frozen=True, slots=True)
class WorkflowExecutionRequest:
    """`ExecuteHealthcareWorkflowUseCase.execute`'s own input DTO —
    bundles the caller-supplied graph (`WorkflowDefinition`), the
    generic clinical bundle (`WorkflowExecutionInput`), and an optional
    `WorkflowCancellationToken` into the single `InputDTO`
    `app.shared.application.use_case.UseCase[InputDTO, OutputDTO]`
    expects, the same "exactly one input DTO" shape every prior AI
    module's own use case takes, rather than a raw multi-argument
    tuple."""

    definition: WorkflowDefinition
    bundle: WorkflowExecutionInput
    cancellation_token: WorkflowCancellationToken | None = None
