"""Tests for `ExecuteHealthcareWorkflowUseCase` — both the audited
`execute` path and the bypassed, progressive `stream_execute` path."""

import pytest

from app.modules.ai_orchestrator.application.dto import WorkflowExecutionRequest
from app.modules.ai_orchestrator.application.services.workflow_executor_service import (
    WorkflowExecutorService,
)
from app.modules.ai_orchestrator.application.services.workflow_planner_service import (
    WorkflowPlannerService,
)
from app.modules.ai_orchestrator.application.services.workflow_result_composer_service import (
    WorkflowResultComposerService,
)
from app.modules.ai_orchestrator.application.services.workflow_validation_service import (
    WorkflowValidationService,
)
from app.modules.ai_orchestrator.application.use_cases.execute_healthcare_workflow import (
    ExecuteHealthcareWorkflowUseCase,
)
from app.modules.ai_orchestrator.domain.enums import (
    WorkflowModule,
    WorkflowStatus,
    WorkflowStepStatus,
)
from app.modules.ai_orchestrator.domain.exceptions import DuplicateModuleExecutionError
from tests.unit.modules.ai_orchestrator.application.fakes import (
    FakeWorkflowExecutorAdapter,
    FakeWorkflowOrchestrationAuditLoggerPort,
    FakeWorkflowPlannerPort,
    make_bundle,
    make_definition,
    make_step,
)


def _make_use_case(
    *adapters: FakeWorkflowExecutorAdapter,
    planner: FakeWorkflowPlannerPort | None = None,
    audit_logger: FakeWorkflowOrchestrationAuditLoggerPort | None = None,
) -> tuple[ExecuteHealthcareWorkflowUseCase, dict[str, object]]:
    validation_service = WorkflowValidationService()
    planner_port = planner or FakeWorkflowPlannerPort()
    planner_service = WorkflowPlannerService(planner_port=planner_port)
    executor_service = WorkflowExecutorService(
        adapters={adapter.module: adapter for adapter in adapters},
        validation_service=validation_service,
    )
    composer_service = WorkflowResultComposerService()
    audit = audit_logger or FakeWorkflowOrchestrationAuditLoggerPort()

    use_case = ExecuteHealthcareWorkflowUseCase(
        validation_service=validation_service,
        planner_service=planner_service,
        executor_service=executor_service,
        composer_service=composer_service,
        audit_logger=audit,
    )
    doubles: dict[str, object] = {"planner": planner_port, "audit_logger": audit}
    return use_case, doubles


class TestExecuteHappyPath:
    async def test_returns_generated_execution_with_result_and_session(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        use_case, _ = _make_use_case(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        generated = await use_case.execute(request)

        assert generated.result.status is WorkflowStatus.COMPLETED
        assert generated.session.workflow_name == definition.name

    async def test_logs_execution_on_success(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        use_case, doubles = _make_use_case(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        await use_case.execute(request)

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeWorkflowOrchestrationAuditLoggerPort)
        assert len(audit_logger.executions) == 1
        assert audit_logger.failures == []

    async def test_chains_completed_step_summaries_into_downstream_context(self) -> None:
        clinical_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        soap_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        use_case, _ = _make_use_case(clinical_note_adapter, soap_note_adapter)
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE),
            make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
        )
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        await use_case.execute(request)

        assert soap_note_adapter.context_calls[0] == {
            WorkflowModule.CLINICAL_NOTE: "clinical_note summary"
        }

    async def test_session_execution_order_matches_the_planner(self) -> None:
        order = (WorkflowModule.SOAP_NOTE, WorkflowModule.CLINICAL_NOTE)
        planner = FakeWorkflowPlannerPort(order=order)
        clinical_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        soap_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        use_case, _ = _make_use_case(clinical_note_adapter, soap_note_adapter, planner=planner)
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.SOAP_NOTE)
        )
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        generated = await use_case.execute(request)

        assert generated.session.execution_order == order

    async def test_seeds_context_from_existing_ai_outputs(self) -> None:
        soap_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        use_case, _ = _make_use_case(soap_note_adapter)
        definition = make_definition(make_step(WorkflowModule.SOAP_NOTE))
        bundle = make_bundle(
            existing_ai_outputs={WorkflowModule.CLINICAL_NOTE: "pre-existing note"}
        )
        request = WorkflowExecutionRequest(definition=definition, bundle=bundle)

        await use_case.execute(request)

        assert soap_note_adapter.context_calls[0] == {
            WorkflowModule.CLINICAL_NOTE: "pre-existing note"
        }


class TestExecuteGraphValidationFailure:
    async def test_invalid_graph_is_logged_and_reraised(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        use_case, doubles = _make_use_case(adapter)
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.CLINICAL_NOTE)
        )
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        with pytest.raises(DuplicateModuleExecutionError):
            await use_case.execute(request)

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeWorkflowOrchestrationAuditLoggerPort)
        assert len(audit_logger.failures) == 1
        assert audit_logger.failures[0]["stage"] == "validate_graph"
        assert audit_logger.failures[0]["error_code"] == "DuplicateModuleExecutionError"

    async def test_invalid_graph_does_not_log_an_execution(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        use_case, doubles = _make_use_case(adapter)
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.CLINICAL_NOTE)
        )
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        with pytest.raises(DuplicateModuleExecutionError):
            await use_case.execute(request)

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeWorkflowOrchestrationAuditLoggerPort)
        assert audit_logger.executions == []


class TestExecuteSessionAggregation:
    async def test_failure_count_reflects_failed_steps(self) -> None:
        failing_adapter = FakeWorkflowExecutorAdapter(
            module=WorkflowModule.CLINICAL_NOTE, error=RuntimeError("boom")
        )
        use_case, _ = _make_use_case(failing_adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE, required=False))
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        generated = await use_case.execute(request)

        assert generated.session.failure_count == 1

    async def test_retry_count_reflects_extra_attempts(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE, fail_times=1)
        use_case, _ = _make_use_case(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE, max_retries=2))
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        generated = await use_case.execute(request)

        assert generated.session.retry_count == 1

    async def test_module_timings_include_every_executed_module(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        use_case, _ = _make_use_case(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        generated = await use_case.execute(request)

        assert WorkflowModule.CLINICAL_NOTE in generated.session.module_timings


class TestStreamExecute:
    async def test_yields_running_then_terminal_event_per_step(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        use_case, _ = _make_use_case(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))

        events = [event async for event in use_case.stream_execute(definition, make_bundle())]

        assert len(events) == 2
        assert events[0].status is WorkflowStepStatus.RUNNING
        assert events[1].status is WorkflowStepStatus.COMPLETED

    async def test_only_the_last_event_is_final(self) -> None:
        clinical_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        soap_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        use_case, _ = _make_use_case(clinical_note_adapter, soap_note_adapter)
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.SOAP_NOTE)
        )

        events = [event async for event in use_case.stream_execute(definition, make_bundle())]

        assert all(not event.is_final for event in events[:-1])
        assert events[-1].is_final is True

    async def test_sequence_numbers_increase_monotonically(self) -> None:
        clinical_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        soap_note_adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.SOAP_NOTE)
        use_case, _ = _make_use_case(clinical_note_adapter, soap_note_adapter)
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.SOAP_NOTE)
        )

        events = [event async for event in use_case.stream_execute(definition, make_bundle())]

        assert [event.sequence for event in events] == [0, 0, 1, 1]

    async def test_streaming_does_not_call_the_audit_logger(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        use_case, doubles = _make_use_case(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))

        async for _event in use_case.stream_execute(definition, make_bundle()):
            pass

        audit_logger = doubles["audit_logger"]
        assert isinstance(audit_logger, FakeWorkflowOrchestrationAuditLoggerPort)
        assert audit_logger.executions == []
