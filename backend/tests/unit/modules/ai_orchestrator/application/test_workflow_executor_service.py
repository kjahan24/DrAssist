"""Tests for `WorkflowExecutorService`."""

from app.modules.ai_orchestrator.application.dto import WorkflowCancellationToken
from app.modules.ai_orchestrator.application.services.workflow_executor_service import (
    WorkflowExecutorService,
)
from app.modules.ai_orchestrator.application.services.workflow_validation_service import (
    WorkflowValidationService,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from tests.unit.modules.ai_orchestrator.application.fakes import (
    FakeWorkflowExecutorAdapter,
    make_bundle,
    make_step,
    make_step_result,
)


def _service(
    *adapters: FakeWorkflowExecutorAdapter,
) -> WorkflowExecutorService:
    return WorkflowExecutorService(
        adapters={adapter.module: adapter for adapter in adapters},
        validation_service=WorkflowValidationService(),
    )


class TestExecuteStepHappyPath:
    async def test_returns_the_adapters_own_result(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        step = make_step(WorkflowModule.CLINICAL_NOTE)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.status is WorkflowStepStatus.COMPLETED
        assert result.summary == "clinical_note summary"
        assert result.attempt_count == 1

    async def test_calls_check_prerequisites_before_execute(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        step = make_step(WorkflowModule.CLINICAL_NOTE)
        service = _service(adapter)
        bundle = make_bundle()

        await service.execute_step(step, bundle, {}, {})

        assert adapter.prerequisite_calls == [bundle]
        assert adapter.execute_calls == [bundle]

    async def test_passes_context_through_to_the_adapter(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        step = make_step(WorkflowModule.SOAP_NOTE)
        service = _service(adapter)
        context = {WorkflowModule.CLINICAL_NOTE: "note text"}

        await service.execute_step(step, make_bundle(), context, {})

        assert adapter.context_calls == [{WorkflowModule.CLINICAL_NOTE: "note text"}]


class TestExecuteStepSkipping:
    async def test_skips_when_prerequisites_are_missing(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.LAB_INTERPRETATION,
            missing_reasons=("no laboratory findings were provided",),
        )
        step = make_step(WorkflowModule.LAB_INTERPRETATION)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.status is WorkflowStepStatus.SKIPPED
        assert result.skipped_reason is not None
        assert "no laboratory findings" in result.skipped_reason

    async def test_does_not_call_execute_when_prerequisites_are_missing(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.LAB_INTERPRETATION, missing_reasons=("missing",)
        )
        step = make_step(WorkflowModule.LAB_INTERPRETATION)
        service = _service(adapter)

        await service.execute_step(step, make_bundle(), {}, {})

        assert adapter.execute_calls == []

    async def test_skips_when_a_dependency_did_not_complete(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        step = make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,))
        service = _service(adapter)
        completed_results = {
            WorkflowModule.CLINICAL_NOTE: make_step_result(
                WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.FAILED, summary=None
            )
        }

        result = await service.execute_step(step, make_bundle(), {}, completed_results)

        assert result.status is WorkflowStepStatus.SKIPPED
        assert adapter.execute_calls == []

    async def test_runs_when_every_dependency_completed(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        step = make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,))
        service = _service(adapter)
        completed_results = {
            WorkflowModule.CLINICAL_NOTE: make_step_result(WorkflowModule.CLINICAL_NOTE)
        }

        result = await service.execute_step(step, make_bundle(), {}, completed_results)

        assert result.status is WorkflowStepStatus.COMPLETED


class TestExecuteStepCancellation:
    async def test_returns_cancelled_when_token_is_already_cancelled(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        step = make_step(WorkflowModule.CLINICAL_NOTE)
        service = _service(adapter)
        token = WorkflowCancellationToken()
        token.cancel()

        result = await service.execute_step(step, make_bundle(), {}, {}, cancellation_token=token)

        assert result.status is WorkflowStepStatus.CANCELLED
        assert adapter.execute_calls == []

    async def test_runs_normally_when_token_is_not_cancelled(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        step = make_step(WorkflowModule.CLINICAL_NOTE)
        service = _service(adapter)
        token = WorkflowCancellationToken()

        result = await service.execute_step(step, make_bundle(), {}, {}, cancellation_token=token)

        assert result.status is WorkflowStepStatus.COMPLETED


class TestExecuteStepFailureIsolation:
    async def test_a_permanent_failure_produces_a_failed_result_not_an_exception(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.CLINICAL_NOTE, error=RuntimeError("provider down")
        )
        step = make_step(WorkflowModule.CLINICAL_NOTE)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.status is WorkflowStepStatus.FAILED
        assert result.error_message == "provider down"

    async def test_failure_does_not_propagate_as_an_exception(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.CLINICAL_NOTE, error=ValueError("bad")
        )
        step = make_step(WorkflowModule.CLINICAL_NOTE)
        service = _service(adapter)

        # Should not raise.
        await service.execute_step(step, make_bundle(), {}, {})


class TestExecuteStepRetry:
    async def test_no_retry_by_default_records_one_attempt(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.CLINICAL_NOTE, error=RuntimeError("fail")
        )
        step = make_step(WorkflowModule.CLINICAL_NOTE, max_retries=0)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.attempt_count == 1
        assert result.status is WorkflowStepStatus.FAILED

    async def test_retries_until_max_retries_then_fails(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.CLINICAL_NOTE, error=RuntimeError("always fails"), fail_times=99
        )
        step = make_step(WorkflowModule.CLINICAL_NOTE, max_retries=2)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.attempt_count == 3
        assert result.status is WorkflowStepStatus.FAILED

    async def test_succeeds_after_transient_failures_within_retry_budget(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE, fail_times=2)
        step = make_step(WorkflowModule.CLINICAL_NOTE, max_retries=2)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.status is WorkflowStepStatus.COMPLETED
        assert result.attempt_count == 3


class TestExecuteStepTimeout:
    async def test_a_step_exceeding_its_timeout_is_recorded_as_failed(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.CLINICAL_NOTE, delay_seconds=0.2
        )
        step = make_step(WorkflowModule.CLINICAL_NOTE, timeout_seconds=0.01)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.status is WorkflowStepStatus.FAILED
        assert result.error_message is not None
        assert "timed out" in result.error_message

    async def test_a_step_finishing_within_its_timeout_completes_normally(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        step = make_step(WorkflowModule.CLINICAL_NOTE, timeout_seconds=5.0)
        service = _service(adapter)

        result = await service.execute_step(step, make_bundle(), {}, {})

        assert result.status is WorkflowStepStatus.COMPLETED
