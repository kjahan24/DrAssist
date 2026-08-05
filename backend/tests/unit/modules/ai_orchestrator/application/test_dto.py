"""Tests for the application-layer DTOs: `GeneratedWorkflowExecution`,
`WorkflowCancellationToken`, `WorkflowExecutionRequest`."""

from uuid import uuid4

from app.modules.ai_orchestrator.application.dto import (
    GeneratedWorkflowExecution,
    WorkflowCancellationToken,
    WorkflowExecutionRequest,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionSession,
    WorkflowResult,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_bundle, make_definition


class TestGeneratedWorkflowExecution:
    def test_construction_bundles_result_and_session(self) -> None:
        result = WorkflowResult(
            workflow_name="wf",
            status=WorkflowStatus.COMPLETED,
            workflow_summary="",
            executed_modules=(),
            skipped_modules=(),
            step_results=(),
            total_execution_time_ms=0.0,
            errors=(),
            warnings=(),
            clinical_summary="",
            confidence_summary=None,
        )
        session = WorkflowExecutionSession(
            execution_id=uuid4(),
            workflow_name="wf",
            execution_order=(),
            total_latency_ms=0.0,
            module_timings={},
            failure_count=0,
            retry_count=0,
            status=WorkflowStatus.COMPLETED,
        )

        generated = GeneratedWorkflowExecution(result=result, session=session)

        assert generated.result is result
        assert generated.session is session


class TestWorkflowCancellationToken:
    def test_starts_not_cancelled(self) -> None:
        token = WorkflowCancellationToken()
        assert token.is_cancelled is False

    def test_cancel_flips_the_flag(self) -> None:
        token = WorkflowCancellationToken()
        token.cancel()
        assert token.is_cancelled is True

    def test_cancel_is_idempotent(self) -> None:
        token = WorkflowCancellationToken()
        token.cancel()
        token.cancel()
        assert token.is_cancelled is True


class TestWorkflowExecutionRequest:
    def test_construction_with_defaults(self) -> None:
        definition = make_definition()
        bundle = make_bundle()

        request = WorkflowExecutionRequest(definition=definition, bundle=bundle)

        assert request.definition is definition
        assert request.bundle is bundle
        assert request.cancellation_token is None

    def test_construction_with_cancellation_token(self) -> None:
        token = WorkflowCancellationToken()
        request = WorkflowExecutionRequest(
            definition=make_definition(), bundle=make_bundle(), cancellation_token=token
        )
        assert request.cancellation_token is token
