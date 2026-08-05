"""Tests for the AI Healthcare Orchestrator module's domain value
objects — construction, `__post_init__` validation, and computed
properties."""

from uuid import uuid4

import pytest

from app.modules.ai_orchestrator.domain.enums import (
    WorkflowModule,
    WorkflowStatus,
    WorkflowStepStatus,
)
from app.modules.ai_orchestrator.domain.exceptions import InvalidWorkflowExecutionInputError
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowDefinition,
    WorkflowExecutionInput,
    WorkflowExecutionSession,
    WorkflowProgressEvent,
    WorkflowResult,
    WorkflowStepDefinition,
    WorkflowStepResult,
)


class TestWorkflowExecutionInput:
    def _valid_kwargs(self) -> dict[str, object]:
        return {
            "organization_id": uuid4(),
            "patient_id": uuid4(),
            "chief_complaint": "Chest pain",
        }

    def test_valid_minimal_construction(self) -> None:
        input_dto = WorkflowExecutionInput(**self._valid_kwargs())  # type: ignore[arg-type]
        assert input_dto.language == "en"
        assert input_dto.medication_list == ()
        assert input_dto.vital_signs == {}
        assert input_dto.existing_ai_outputs == {}

    def test_blank_chief_complaint_raises(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["chief_complaint"] = "   "
        with pytest.raises(InvalidWorkflowExecutionInputError):
            WorkflowExecutionInput(**kwargs)  # type: ignore[arg-type]

    def test_blank_language_raises(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["language"] = "   "
        with pytest.raises(InvalidWorkflowExecutionInputError):
            WorkflowExecutionInput(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("patient_age", [-1, 151])
    def test_out_of_range_patient_age_raises(self, patient_age: int) -> None:
        kwargs = self._valid_kwargs()
        kwargs["patient_age"] = patient_age
        with pytest.raises(InvalidWorkflowExecutionInputError):
            WorkflowExecutionInput(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("patient_age", [0, 150])
    def test_boundary_patient_age_is_valid(self, patient_age: int) -> None:
        kwargs = self._valid_kwargs()
        kwargs["patient_age"] = patient_age
        input_dto = WorkflowExecutionInput(**kwargs)  # type: ignore[arg-type]
        assert input_dto.patient_age == patient_age

    def test_carries_through_optional_bundles(self) -> None:
        kwargs = self._valid_kwargs()
        kwargs["medication_list"] = ("Lisinopril",)
        kwargs["diagnoses"] = ("Hypertension",)
        kwargs["vital_signs"] = {"heart_rate": "80"}
        input_dto = WorkflowExecutionInput(**kwargs)  # type: ignore[arg-type]
        assert input_dto.medication_list == ("Lisinopril",)
        assert input_dto.diagnoses == ("Hypertension",)
        assert input_dto.vital_signs == {"heart_rate": "80"}


class TestWorkflowStepDefinition:
    def test_valid_minimal_construction(self) -> None:
        step = WorkflowStepDefinition(module=WorkflowModule.CLINICAL_NOTE)
        assert step.depends_on == ()
        assert step.required is True
        assert step.max_retries == 0
        assert step.timeout_seconds is None

    def test_negative_max_retries_raises(self) -> None:
        with pytest.raises(InvalidWorkflowExecutionInputError):
            WorkflowStepDefinition(module=WorkflowModule.CLINICAL_NOTE, max_retries=-1)

    def test_zero_max_retries_is_valid(self) -> None:
        step = WorkflowStepDefinition(module=WorkflowModule.CLINICAL_NOTE, max_retries=0)
        assert step.max_retries == 0

    @pytest.mark.parametrize("timeout_seconds", [0.0, -1.0])
    def test_non_positive_timeout_raises(self, timeout_seconds: float) -> None:
        with pytest.raises(InvalidWorkflowExecutionInputError):
            WorkflowStepDefinition(
                module=WorkflowModule.CLINICAL_NOTE, timeout_seconds=timeout_seconds
            )

    def test_positive_timeout_is_valid(self) -> None:
        step = WorkflowStepDefinition(module=WorkflowModule.CLINICAL_NOTE, timeout_seconds=5.0)
        assert step.timeout_seconds == 5.0

    def test_optional_step_construction(self) -> None:
        step = WorkflowStepDefinition(
            module=WorkflowModule.RADIOLOGY_INTERPRETATION, required=False
        )
        assert step.required is False

    def test_depends_on_stored(self) -> None:
        step = WorkflowStepDefinition(
            module=WorkflowModule.SOAP_NOTE, depends_on=(WorkflowModule.CLINICAL_NOTE,)
        )
        assert step.depends_on == (WorkflowModule.CLINICAL_NOTE,)


class TestWorkflowDefinition:
    def test_valid_construction(self) -> None:
        definition = WorkflowDefinition(
            name="basic", steps=(WorkflowStepDefinition(module=WorkflowModule.CLINICAL_NOTE),)
        )
        assert definition.name == "basic"
        assert len(definition.steps) == 1

    def test_blank_name_raises(self) -> None:
        with pytest.raises(InvalidWorkflowExecutionInputError):
            WorkflowDefinition(
                name="   ", steps=(WorkflowStepDefinition(module=WorkflowModule.CLINICAL_NOTE),)
            )

    def test_empty_steps_raises(self) -> None:
        with pytest.raises(InvalidWorkflowExecutionInputError):
            WorkflowDefinition(name="empty", steps=())


class TestWorkflowStepResult:
    def test_defaults(self) -> None:
        result = WorkflowStepResult(
            module=WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.PENDING
        )
        assert result.summary is None
        assert result.confidence_score is None
        assert result.latency_ms == 0.0
        assert result.attempt_count == 0
        assert result.error_message is None
        assert result.skipped_reason is None

    def test_completed_result_construction(self) -> None:
        result = WorkflowStepResult(
            module=WorkflowModule.CLINICAL_NOTE,
            status=WorkflowStepStatus.COMPLETED,
            summary="note text",
            confidence_score=0.8,
            latency_ms=12.5,
            attempt_count=1,
        )
        assert result.summary == "note text"
        assert result.confidence_score == 0.8


class TestWorkflowResult:
    def test_construction(self) -> None:
        result = WorkflowResult(
            workflow_name="basic",
            status=WorkflowStatus.COMPLETED,
            workflow_summary="Executed 1 of 1 module(s)",
            executed_modules=(WorkflowModule.CLINICAL_NOTE,),
            skipped_modules=(),
            step_results=(),
            total_execution_time_ms=10.0,
            errors=(),
            warnings=(),
            clinical_summary="summary",
            confidence_summary=0.5,
        )
        assert result.status is WorkflowStatus.COMPLETED
        assert result.confidence_summary == 0.5


class TestWorkflowExecutionSession:
    def test_construction(self) -> None:
        session = WorkflowExecutionSession(
            execution_id=uuid4(),
            workflow_name="basic",
            execution_order=(WorkflowModule.CLINICAL_NOTE,),
            total_latency_ms=10.0,
            module_timings={WorkflowModule.CLINICAL_NOTE: 10.0},
            failure_count=0,
            retry_count=0,
            status=WorkflowStatus.COMPLETED,
        )
        assert session.failure_count == 0
        assert session.created_at is not None


class TestWorkflowProgressEvent:
    def test_default_is_final_false(self) -> None:
        event = WorkflowProgressEvent(
            module=WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.RUNNING, sequence=0
        )
        assert event.is_final is False

    def test_is_final_true(self) -> None:
        event = WorkflowProgressEvent(
            module=WorkflowModule.CLINICAL_NOTE,
            status=WorkflowStepStatus.COMPLETED,
            sequence=0,
            is_final=True,
        )
        assert event.is_final is True
