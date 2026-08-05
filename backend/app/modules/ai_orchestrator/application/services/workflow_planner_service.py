"""`WorkflowPlannerService` — this task's own explicitly-named
APPLICATION service, the thin orchestration layer over
`WorkflowPlannerPort` that computes one valid execution order for an
already-validated `WorkflowDefinition`, per this task's own "Support
dependency ordering" requirement.
"""

from app.modules.ai_orchestrator.application.ports import WorkflowPlannerPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from app.modules.ai_orchestrator.domain.value_objects import WorkflowDefinition


class WorkflowPlannerService:
    def __init__(self, *, planner_port: WorkflowPlannerPort) -> None:
        self._planner_port = planner_port

    def plan(self, definition: WorkflowDefinition) -> tuple[WorkflowModule, ...]:
        return self._planner_port.compute_execution_order(definition)
