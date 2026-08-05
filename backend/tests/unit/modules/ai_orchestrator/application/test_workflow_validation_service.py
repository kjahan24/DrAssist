"""Tests for `WorkflowValidationService`."""

import pytest

from app.modules.ai_orchestrator.application.services.workflow_validation_service import (
    WorkflowValidationService,
)
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.exceptions import (
    CircularDependencyError,
    DuplicateModuleExecutionError,
    InvalidWorkflowGraphError,
    MissingModuleOutputError,
    MissingPrerequisiteError,
)
from app.modules.ai_orchestrator.domain.value_objects import WorkflowDefinition
from tests.unit.modules.ai_orchestrator.application.fakes import make_step, make_step_result


def _service() -> WorkflowValidationService:
    return WorkflowValidationService()


class TestValidateGraphHappyPath:
    def test_accepts_a_single_step_workflow(self) -> None:
        definition = WorkflowDefinition(
            name="single", steps=(make_step(WorkflowModule.CLINICAL_NOTE),)
        )
        _service().validate_graph(definition)

    def test_accepts_a_linear_chain(self) -> None:
        definition = WorkflowDefinition(
            name="chain",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
                make_step(WorkflowModule.ICD10_CODING, depends_on=(WorkflowModule.SOAP_NOTE,)),
            ),
        )
        _service().validate_graph(definition)

    def test_accepts_independent_branches(self) -> None:
        definition = WorkflowDefinition(
            name="branches",
            steps=(
                make_step(WorkflowModule.LAB_INTERPRETATION),
                make_step(WorkflowModule.RADIOLOGY_INTERPRETATION),
                make_step(WorkflowModule.PATHOLOGY_INTERPRETATION),
            ),
        )
        _service().validate_graph(definition)


class TestValidateGraphDuplicateExecution:
    def test_raises_when_a_module_is_listed_twice(self) -> None:
        definition = WorkflowDefinition(
            name="dup",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE),
                make_step(WorkflowModule.CLINICAL_NOTE),
            ),
        )
        with pytest.raises(DuplicateModuleExecutionError) as exc_info:
            _service().validate_graph(definition)
        assert exc_info.value.module == "clinical_note"


class TestValidateGraphInvalidGraph:
    def test_raises_when_a_dependency_is_not_part_of_the_workflow(self) -> None:
        definition = WorkflowDefinition(
            name="dangling",
            steps=(
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
            ),
        )
        with pytest.raises(InvalidWorkflowGraphError):
            _service().validate_graph(definition)


class TestValidateGraphCircularDependency:
    def test_raises_for_a_direct_two_node_cycle(self) -> None:
        definition = WorkflowDefinition(
            name="cycle",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE, depends_on=(WorkflowModule.SOAP_NOTE,)),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
            ),
        )
        with pytest.raises(CircularDependencyError):
            _service().validate_graph(definition)

    def test_raises_for_a_self_dependency(self) -> None:
        definition = WorkflowDefinition(
            name="self-cycle",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
            ),
        )
        with pytest.raises(CircularDependencyError):
            _service().validate_graph(definition)

    def test_raises_for_a_three_node_cycle(self) -> None:
        definition = WorkflowDefinition(
            name="triangle",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE, depends_on=(WorkflowModule.ICD10_CODING,)),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
                make_step(WorkflowModule.ICD10_CODING, depends_on=(WorkflowModule.SOAP_NOTE,)),
            ),
        )
        with pytest.raises(CircularDependencyError):
            _service().validate_graph(definition)

    def test_does_not_raise_when_no_cycle_exists_alongside_a_deep_chain(self) -> None:
        definition = WorkflowDefinition(
            name="deep-chain",
            steps=(
                make_step(WorkflowModule.CLINICAL_NOTE),
                make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)),
                make_step(WorkflowModule.ICD10_CODING, depends_on=(WorkflowModule.SOAP_NOTE,)),
                make_step(WorkflowModule.PRESCRIPTION, depends_on=(WorkflowModule.ICD10_CODING,)),
                make_step(
                    WorkflowModule.DRUG_INTERACTION, depends_on=(WorkflowModule.PRESCRIPTION,)
                ),
            ),
        )
        _service().validate_graph(definition)


class TestValidatePrerequisites:
    def test_raises_when_reasons_are_given(self) -> None:
        step = make_step(WorkflowModule.LAB_INTERPRETATION)
        with pytest.raises(MissingPrerequisiteError) as exc_info:
            _service().validate_prerequisites(step, ("no findings",))
        assert exc_info.value.module == "lab_interpretation"

    def test_does_not_raise_when_no_reasons_are_given(self) -> None:
        step = make_step(WorkflowModule.LAB_INTERPRETATION)
        _service().validate_prerequisites(step, ())

    def test_joins_multiple_reasons_in_the_message(self) -> None:
        step = make_step(WorkflowModule.PATIENT_EDUCATION)
        with pytest.raises(MissingPrerequisiteError) as exc_info:
            _service().validate_prerequisites(step, ("no diagnoses", "no medications"))
        assert "no diagnoses" in str(exc_info.value)
        assert "no medications" in str(exc_info.value)


class TestValidateModuleOutputs:
    def test_does_not_raise_when_step_has_no_dependencies(self) -> None:
        step = make_step(WorkflowModule.CLINICAL_NOTE)
        _service().validate_module_outputs(step, {})

    def test_does_not_raise_when_every_dependency_completed(self) -> None:
        step = make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,))
        completed = {WorkflowModule.CLINICAL_NOTE: make_step_result(WorkflowModule.CLINICAL_NOTE)}
        _service().validate_module_outputs(step, completed)

    def test_raises_when_a_dependency_is_missing_entirely(self) -> None:
        step = make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,))
        with pytest.raises(MissingModuleOutputError) as exc_info:
            _service().validate_module_outputs(step, {})
        assert exc_info.value.module == "soap_note"
        assert exc_info.value.dependency == "clinical_note"

    def test_raises_when_a_dependency_was_skipped(self) -> None:
        step = make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,))
        completed = {
            WorkflowModule.CLINICAL_NOTE: make_step_result(
                WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.SKIPPED, summary=None
            )
        }
        with pytest.raises(MissingModuleOutputError):
            _service().validate_module_outputs(step, completed)

    def test_raises_when_a_dependency_failed(self) -> None:
        step = make_step(WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,))
        completed = {
            WorkflowModule.CLINICAL_NOTE: make_step_result(
                WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.FAILED, summary=None
            )
        }
        with pytest.raises(MissingModuleOutputError):
            _service().validate_module_outputs(step, completed)
