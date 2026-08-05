"""The AI Healthcare Orchestrator module's public port — the only
contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.ai_orchestrator.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module.

Named `HealthcareWorkflowPort`, per this task's own literal "Create
ports: HealthcareWorkflowPort, ..." wording, rather than the
"`<Module>AIPort`" convention every prior AI module's own public port
follows — this task's own GOAL section is explicit that "It is NOT
another AI model. It is the orchestration layer", so this port is named
for what it actually is instead. See `application/ports.py`'s own
module docstring for the full "why this name lives here, not among the
other two explicitly-named application-layer ports" reasoning.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.ai_orchestrator.public.dto import (
    GeneratedWorkflowExecution,
    WorkflowExecutionRequest,
    WorkflowProgressEvent,
)


class HealthcareWorkflowPort(ABC):
    @abstractmethod
    async def execute_workflow(
        self, request: WorkflowExecutionRequest
    ) -> GeneratedWorkflowExecution: ...

    @abstractmethod
    def stream_execute_workflow(
        self, request: WorkflowExecutionRequest
    ) -> AsyncIterator[WorkflowProgressEvent]: ...
