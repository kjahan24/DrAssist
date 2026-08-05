"""Domain exceptions for the AI Healthcare Orchestrator module.

Mapped one-to-one onto this task's own five-item VALIDATION list:
"invalid workflow graph" -> `InvalidWorkflowGraphError`, "circular
dependency" -> `CircularDependencyError`, "duplicate execution" ->
`DuplicateModuleExecutionError` (all three raised by
`WorkflowValidationService.validate_graph`, a static check of the
caller-supplied `WorkflowDefinition` shape, before any step ever runs);
"missing prerequisites" -> `MissingPrerequisiteError` (raised only when
a workflow is configured to treat a step's own unmet prerequisites as
fatal rather than skippable — see `WorkflowExecutorService`'s own
module docstring for why the *default* behavior is to skip, not raise);
"missing module outputs" -> `MissingModuleOutputError` (raised when a
step's own declared dependency did not produce a usable output —
skipped or failed — checked at execution time, since it depends on what
actually happened during *this* run, not just the static graph shape).
`InvalidWorkflowExecutionInputError` covers the remaining, not-
separately-named baseline input checks (a blank `chief_complaint`, a
blank `language`, an out-of-range `patient_age`) every prior AI module's
own top-level input value object also performs for itself.

Errors originating from any of the twelve orchestrated peer modules
(their own domain exceptions, or AI Foundation errors propagating
through them) are **not** wrapped or re-typed here — this module cannot
import any peer module's `.domain` from outside that module (module-
independence rule), so it cannot `isinstance`-check or re-wrap a peer's
own exception; `infrastructure/module_adapters/*.py` therefore catches
peer failures via the broadest safe boundary (`except Exception`), the
same "failure isolation" this task's own ERROR HANDLING section asks
for, converting any peer failure into a `WorkflowStepResult` with
`status=FAILED` rather than letting one step's exception type leak into
this module's own domain vocabulary.
"""

from app.shared.domain.exceptions import DomainError


class InvalidWorkflowExecutionInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid workflow execution input: {reason}")
        self.reason = reason


class InvalidWorkflowGraphError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid workflow graph: {reason}")
        self.reason = reason


class CircularDependencyError(DomainError):
    def __init__(self, cycle: tuple[str, ...]) -> None:
        super().__init__(f"circular dependency detected: {' -> '.join(cycle)}")
        self.cycle = cycle


class DuplicateModuleExecutionError(DomainError):
    def __init__(self, module: str) -> None:
        super().__init__(f"module {module!r} is listed more than once in the workflow")
        self.module = module


class MissingPrerequisiteError(DomainError):
    def __init__(self, module: str, reason: str) -> None:
        super().__init__(f"module {module!r} is missing a prerequisite: {reason}")
        self.module = module
        self.reason = reason


class MissingModuleOutputError(DomainError):
    def __init__(self, module: str, dependency: str) -> None:
        super().__init__(
            f"module {module!r} depends on {dependency!r}, which produced no usable output"
        )
        self.module = module
        self.dependency = dependency
