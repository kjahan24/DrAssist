"""Unit tests for `DeterministicWorkflowPlanner`."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from app.modules.ai_orchestrator.domain.value_objects import WorkflowDefinition
from app.modules.ai_orchestrator.infrastructure.planning.topological_workflow_planner import (
    DeterministicWorkflowPlanner,
)
from tests.unit.modules.ai_orchestrator.application.fakes import make_step

_PLANNER = DeterministicWorkflowPlanner()


class TestComputeExecutionOrder:
    def test_single_step(self) -> None:
        definition = WorkflowDefinition(
            name="single", steps=(make_step(WorkflowModule.CLINICAL_NOTE),)
        )
        assert _PLANNER.compute_execution_order(definition) == (WorkflowModule.CLINICAL_NOTE,)

    def test_linear_chain_preserves_dependency_order(self) -> None:
        definition = WorkflowDefinition(
            name="chain",
            steps=(
                make_step(WorkflowModule.ICD10_CODING, depends_on=(WorkflowModule.SOAP_NOTE,)),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
                make_step(WorkflowModule.CLINICAL_NOTE),
            ),
        )

        order = _PLANNER.compute_execution_order(definition)

        assert order.index(WorkflowModule.CLINICAL_NOTE) < order.index(WorkflowModule.SOAP_NOTE)
        assert order.index(WorkflowModule.SOAP_NOTE) < order.index(WorkflowModule.ICD10_CODING)

    def test_independent_steps_preserve_declaration_order(self) -> None:
        definition = WorkflowDefinition(
            name="independent",
            steps=(
                make_step(WorkflowModule.LAB_INTERPRETATION),
                make_step(WorkflowModule.RADIOLOGY_INTERPRETATION),
                make_step(WorkflowModule.PATHOLOGY_INTERPRETATION),
            ),
        )

        order = _PLANNER.compute_execution_order(definition)

        assert order == (
            WorkflowModule.LAB_INTERPRETATION,
            WorkflowModule.RADIOLOGY_INTERPRETATION,
            WorkflowModule.PATHOLOGY_INTERPRETATION,
        )

    def test_diamond_shaped_graph(self) -> None:
        definition = WorkflowDefinition(
            name="diamond",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
                make_step(
                    WorkflowModule.DIFFERENTIAL_DIAGNOSIS,
                    depends_on=(WorkflowModule.CLINICAL_NOTE,),
                ),
                make_step(
                    WorkflowModule.ICD10_CODING,
                    depends_on=(WorkflowModule.SOAP_NOTE, WorkflowModule.DIFFERENTIAL_DIAGNOSIS),
                ),
            ),
        )

        order = _PLANNER.compute_execution_order(definition)

        assert order.index(WorkflowModule.CLINICAL_NOTE) < order.index(WorkflowModule.SOAP_NOTE)
        assert order.index(WorkflowModule.CLINICAL_NOTE) < order.index(
            WorkflowModule.DIFFERENTIAL_DIAGNOSIS
        )
        assert order.index(WorkflowModule.SOAP_NOTE) < order.index(WorkflowModule.ICD10_CODING)
        assert order.index(WorkflowModule.DIFFERENTIAL_DIAGNOSIS) < order.index(
            WorkflowModule.ICD10_CODING
        )

    def test_result_contains_every_step_exactly_once(self) -> None:
        definition = WorkflowDefinition(
            name="full",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
                make_step(WorkflowModule.ICD10_CODING, depends_on=(WorkflowModule.SOAP_NOTE,)),
            ),
        )

        order = _PLANNER.compute_execution_order(definition)

        assert len(order) == 3
        assert len(set(order)) == 3

    def test_defensively_appends_unresolvable_steps_instead_of_looping_forever(self) -> None:
        definition = WorkflowDefinition(
            name="cyclic",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE, depends_on=(WorkflowModule.SOAP_NOTE,)),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
            ),
        )

        order = _PLANNER.compute_execution_order(definition)

        assert set(order) == {WorkflowModule.CLINICAL_NOTE, WorkflowModule.SOAP_NOTE}
