"""`DeterministicWorkflowPlanner` — the one concrete `WorkflowPlannerPort`
implementation this task ships: a standard, deterministic topological
sort over a `WorkflowDefinition`'s own `depends_on` edges.

Deliberately assumes the given `definition` is already acyclic —
`WorkflowValidationService.validate_graph` is always called first in
`ExecuteHealthcareWorkflowUseCase`'s own pipeline (see that use case's
own module docstring), so this planner does not re-detect cycles itself;
if it is ever called directly against an invalid graph anyway (e.g. in
a unit test exercising this class in isolation), any step whose own
dependency is never resolved is appended in its original declared order
at the end, rather than looping forever — a defensive fallback, not this
module's own primary cycle-handling path.

Multiple simultaneously-ready steps (no unresolved dependency) are
ordered by their original position in `definition.steps` — deterministic
and reproducible, so the same `WorkflowDefinition` always produces the
same execution order across repeated runs and across test assertions.
"""

from app.modules.ai_orchestrator.application.ports import WorkflowPlannerPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from app.modules.ai_orchestrator.domain.value_objects import WorkflowDefinition


class DeterministicWorkflowPlanner(WorkflowPlannerPort):
    def compute_execution_order(self, definition: WorkflowDefinition) -> tuple[WorkflowModule, ...]:
        steps_by_module = {step.module: step for step in definition.steps}
        remaining = list(steps_by_module.keys())
        resolved: set[WorkflowModule] = set()
        order: list[WorkflowModule] = []

        while remaining:
            progressed = False
            for module in list(remaining):
                step = steps_by_module[module]
                if all(dependency in resolved for dependency in step.depends_on):
                    order.append(module)
                    resolved.add(module)
                    remaining.remove(module)
                    progressed = True
            if not progressed:
                order.extend(remaining)
                break

        return tuple(order)
