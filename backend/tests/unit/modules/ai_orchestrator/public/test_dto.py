"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.ai_orchestrator.application.dto import (
    GeneratedWorkflowExecution as ApplicationGeneratedWorkflowExecution,
)
from app.modules.ai_orchestrator.application.dto import (
    WorkflowCancellationToken as ApplicationWorkflowCancellationToken,
)
from app.modules.ai_orchestrator.application.dto import (
    WorkflowExecutionRequest as ApplicationWorkflowExecutionRequest,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule as DomainWorkflowModule
from app.modules.ai_orchestrator.domain.enums import WorkflowStatus as DomainWorkflowStatus
from app.modules.ai_orchestrator.domain.enums import (
    WorkflowStepStatus as DomainWorkflowStepStatus,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition as DomainWorkflowDefinition,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput as DomainWorkflowExecutionInput,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionSession as DomainWorkflowExecutionSession,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowProgressEvent as DomainWorkflowProgressEvent,
)
from app.modules.ai_orchestrator.domain.value_objects import WorkflowResult as DomainWorkflowResult
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowStepDefinition as DomainWorkflowStepDefinition,
)
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowStepResult as DomainWorkflowStepResult,
)
from app.modules.ai_orchestrator.public.dto import (
    GeneratedWorkflowExecution,
    WorkflowCancellationToken,
    WorkflowDefinition,
    WorkflowExecutionInput,
    WorkflowExecutionRequest,
    WorkflowExecutionSession,
    WorkflowModule,
    WorkflowProgressEvent,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepResult,
    WorkflowStepStatus,
)


class TestPublicDtoReExports:
    def test_generated_workflow_execution_is_the_application_type(self) -> None:
        assert GeneratedWorkflowExecution is ApplicationGeneratedWorkflowExecution

    def test_workflow_cancellation_token_is_the_application_type(self) -> None:
        assert WorkflowCancellationToken is ApplicationWorkflowCancellationToken

    def test_workflow_execution_request_is_the_application_type(self) -> None:
        assert WorkflowExecutionRequest is ApplicationWorkflowExecutionRequest

    def test_workflow_module_is_the_domain_type(self) -> None:
        assert WorkflowModule is DomainWorkflowModule

    def test_workflow_status_is_the_domain_type(self) -> None:
        assert WorkflowStatus is DomainWorkflowStatus

    def test_workflow_step_status_is_the_domain_type(self) -> None:
        assert WorkflowStepStatus is DomainWorkflowStepStatus

    def test_workflow_definition_is_the_domain_type(self) -> None:
        assert WorkflowDefinition is DomainWorkflowDefinition

    def test_workflow_execution_input_is_the_domain_type(self) -> None:
        assert WorkflowExecutionInput is DomainWorkflowExecutionInput

    def test_workflow_execution_session_is_the_domain_type(self) -> None:
        assert WorkflowExecutionSession is DomainWorkflowExecutionSession

    def test_workflow_progress_event_is_the_domain_type(self) -> None:
        assert WorkflowProgressEvent is DomainWorkflowProgressEvent

    def test_workflow_result_is_the_domain_type(self) -> None:
        assert WorkflowResult is DomainWorkflowResult

    def test_workflow_step_definition_is_the_domain_type(self) -> None:
        assert WorkflowStepDefinition is DomainWorkflowStepDefinition

    def test_workflow_step_result_is_the_domain_type(self) -> None:
        assert WorkflowStepResult is DomainWorkflowStepResult
