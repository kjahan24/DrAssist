"""Tests for `WorkflowPlannerService`."""

from app.modules.ai_orchestrator.application.services.workflow_planner_service import (
    WorkflowPlannerService,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from tests.unit.modules.ai_orchestrator.application.fakes import (
    FakeWorkflowPlannerPort,
    make_definition,
    make_step,
)


class TestPlan:
    def test_delegates_to_the_port(self) -> None:
        port = FakeWorkflowPlannerPort(order=(WorkflowModule.CLINICAL_NOTE,))
        service = WorkflowPlannerService(planner_port=port)
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))

        result = service.plan(definition)

        assert result == (WorkflowModule.CLINICAL_NOTE,)
        assert port.calls == [definition]

    def test_returns_whatever_the_port_computes(self) -> None:
        order = (WorkflowModule.SOAP_NOTE, WorkflowModule.CLINICAL_NOTE)
        port = FakeWorkflowPlannerPort(order=order)
        service = WorkflowPlannerService(planner_port=port)

        result = service.plan(make_definition())

        assert result == order
