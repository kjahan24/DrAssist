"""`WorkflowValidationService` — this task's own explicitly-named
APPLICATION service, covering four of this task's own five VALIDATION
categories (the fifth, "malformed JSON", does not apply to this module
at all — it makes no AI call of its own to parse a response from):

- `validate_graph` — this task's own "invalid workflow graph"/"circular
  dependency"/"duplicate execution" categories, checked once, always
  strictly (never gracefully degraded — a workflow graph that is
  self-contradictory cannot be safely executed at all, partially or
  otherwise). Duplicate-module detection is a simple set-membership
  scan; dangling-dependency detection checks every `depends_on` entry
  names a module actually present in the same workflow; circular-
  dependency detection is a standard three-color depth-first search,
  returning the actual cycle members in the raised
  `CircularDependencyError` rather than just "a cycle exists somewhere".
- `validate_prerequisites`/`validate_module_outputs` — this task's own
  "missing prerequisites"/"missing module outputs" categories. Pure,
  raising validators — `WorkflowExecutorService` is the one call site
  that *catches* what these raise and converts it into a skipped step
  rather than a fatal error (see that service's own docstring for the
  "Support skipping modules"/"graceful degradation" reasoning); a
  future strict-mode caller could call either method directly and let
  the exception propagate instead.
"""

from collections.abc import Mapping

from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.exceptions import (
    CircularDependencyError,
    DuplicateModuleExecutionError,
    InvalidWorkflowGraphError,
    MissingModuleOutputError,
    MissingPrerequisiteError,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition,
    WorkflowStepDefinition,
    WorkflowStepResult,
)

_WHITE, _GRAY, _BLACK = 0, 1, 2


class WorkflowValidationService:
    def validate_graph(self, definition: WorkflowDefinition) -> None:
        self._check_duplicates(definition)
        self._check_dangling_dependencies(definition)
        self._check_circular_dependencies(definition)

    def validate_prerequisites(
        self, step: WorkflowStepDefinition, missing_reasons: tuple[str, ...]
    ) -> None:
        if missing_reasons:
            raise MissingPrerequisiteError(step.module.value, "; ".join(missing_reasons))

    def validate_module_outputs(
        self,
        step: WorkflowStepDefinition,
        completed_results: Mapping[WorkflowModule, WorkflowStepResult],
    ) -> None:
        for dependency in step.depends_on:
            dependency_result = completed_results.get(dependency)
            if (
                dependency_result is None
                or dependency_result.status is not WorkflowStepStatus.COMPLETED
            ):
                raise MissingModuleOutputError(step.module.value, dependency.value)

    def _check_duplicates(self, definition: WorkflowDefinition) -> None:
        seen: set[WorkflowModule] = set()
        for step in definition.steps:
            if step.module in seen:
                raise DuplicateModuleExecutionError(step.module.value)
            seen.add(step.module)

    def _check_dangling_dependencies(self, definition: WorkflowDefinition) -> None:
        known = {step.module for step in definition.steps}
        for step in definition.steps:
            for dependency in step.depends_on:
                if dependency not in known:
                    raise InvalidWorkflowGraphError(
                        f"step {step.module.value!r} depends on {dependency.value!r}, which "
                        "is not part of this workflow"
                    )

    def _check_circular_dependencies(self, definition: WorkflowDefinition) -> None:
        graph = {step.module: step.depends_on for step in definition.steps}
        color: dict[WorkflowModule, int] = dict.fromkeys(graph, _WHITE)
        path: list[WorkflowModule] = []

        def visit(module: WorkflowModule) -> None:
            color[module] = _GRAY
            path.append(module)
            for dependency in graph[module]:
                if color[dependency] == _GRAY:
                    cycle_start = path.index(dependency)
                    cycle = tuple(m.value for m in path[cycle_start:]) + (dependency.value,)
                    raise CircularDependencyError(cycle)
                if color[dependency] == _WHITE:
                    visit(dependency)
            path.pop()
            color[module] = _BLACK

        for module in graph:
            if color[module] == _WHITE:
                visit(module)
