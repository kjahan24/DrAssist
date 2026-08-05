"""Unit tests for `container.py`'s DI wiring."""

from app.modules.ai_orchestrator.container import (
    get_execute_healthcare_workflow_use_case,
    get_healthcare_orchestrator_facade,
    get_workflow_adapters,
    get_workflow_executor_service,
    get_workflow_orchestration_audit_logger,
    get_workflow_planner_port,
    get_workflow_planner_service,
    get_workflow_result_composer_service,
    get_workflow_validation_service,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from app.modules.ai_orchestrator.public.facade import HealthcareOrchestratorFacade


class TestGetHealthcareOrchestratorFacade:
    def test_returns_a_healthcare_orchestrator_facade(self) -> None:
        assert isinstance(get_healthcare_orchestrator_facade(), HealthcareOrchestratorFacade)

    def test_is_a_singleton(self) -> None:
        assert get_healthcare_orchestrator_facade() is get_healthcare_orchestrator_facade()


class TestGetWorkflowAdapters:
    def test_wires_all_twelve_workflow_modules(self) -> None:
        adapters = get_workflow_adapters()
        assert set(adapters.keys()) == set(WorkflowModule)

    def test_each_adapter_reports_its_own_module(self) -> None:
        adapters = get_workflow_adapters()
        for module, adapter in adapters.items():
            assert adapter.module == module

    def test_is_a_singleton(self) -> None:
        assert get_workflow_adapters() is get_workflow_adapters()


class TestSingletonHelpers:
    def test_workflow_planner_port_is_a_singleton(self) -> None:
        assert get_workflow_planner_port() is get_workflow_planner_port()

    def test_workflow_validation_service_is_a_singleton(self) -> None:
        assert get_workflow_validation_service() is get_workflow_validation_service()

    def test_workflow_planner_service_is_a_singleton(self) -> None:
        assert get_workflow_planner_service() is get_workflow_planner_service()

    def test_workflow_executor_service_is_a_singleton(self) -> None:
        assert get_workflow_executor_service() is get_workflow_executor_service()

    def test_workflow_result_composer_service_is_a_singleton(self) -> None:
        assert get_workflow_result_composer_service() is get_workflow_result_composer_service()

    def test_workflow_orchestration_audit_logger_is_a_singleton(self) -> None:
        logger_a = get_workflow_orchestration_audit_logger()
        logger_b = get_workflow_orchestration_audit_logger()
        assert logger_a is logger_b

    def test_execute_healthcare_workflow_use_case_is_a_singleton(self) -> None:
        assert (
            get_execute_healthcare_workflow_use_case() is get_execute_healthcare_workflow_use_case()
        )
