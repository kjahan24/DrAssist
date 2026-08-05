"""Unit tests for `HealthcareOrchestratorFacade` — exercised through
`HealthcareWorkflowPort` exactly as a future consumer module would call
it, per `docs/backend-architecture/12_testing_architecture.md`'s
"Contract tests" framing."""

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
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStatus
from app.modules.ai_orchestrator.public.dto import WorkflowExecutionRequest
from app.modules.ai_orchestrator.public.facade import HealthcareOrchestratorFacade
from app.modules.ai_orchestrator.public.interfaces import HealthcareWorkflowPort
from tests.unit.modules.ai_orchestrator.application.fakes import (
    FakeWorkflowExecutorAdapter,
    FakeWorkflowOrchestrationAuditLoggerPort,
    FakeWorkflowPlannerPort,
    make_bundle,
    make_definition,
    make_step,
)


def _facade(*adapters: FakeWorkflowExecutorAdapter) -> HealthcareOrchestratorFacade:
    validation_service = WorkflowValidationService()
    executor_service = WorkflowExecutorService(
        adapters={adapter.module: adapter for adapter in adapters},
        validation_service=validation_service,
    )
    use_case = ExecuteHealthcareWorkflowUseCase(
        validation_service=validation_service,
        planner_service=WorkflowPlannerService(planner_port=FakeWorkflowPlannerPort()),
        executor_service=executor_service,
        composer_service=WorkflowResultComposerService(),
        audit_logger=FakeWorkflowOrchestrationAuditLoggerPort(),
    )
    return HealthcareOrchestratorFacade(execute_use_case=use_case)


class TestHealthcareOrchestratorFacade:
    def test_is_a_healthcare_workflow_port(self) -> None:
        assert isinstance(_facade(), HealthcareWorkflowPort)

    async def test_execute_workflow_delegates_to_the_use_case(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        facade = _facade(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        generated = await facade.execute_workflow(request)

        assert generated.result.status is WorkflowStatus.COMPLETED
        assert generated.session.workflow_name == definition.name

    async def test_stream_execute_workflow_delegates_to_the_use_case(self) -> None:
        adapter = FakeWorkflowExecutorAdapter(module=WorkflowModule.CLINICAL_NOTE)
        facade = _facade(adapter)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        request = WorkflowExecutionRequest(definition=definition, bundle=make_bundle())

        events = [event async for event in facade.stream_execute_workflow(request)]

        assert len(events) == 2
        assert events[-1].is_final is True
