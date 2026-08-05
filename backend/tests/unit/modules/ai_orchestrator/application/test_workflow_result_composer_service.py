"""Tests for `WorkflowResultComposerService`."""

from app.modules.ai_orchestrator.application.services.workflow_result_composer_service import (
    WorkflowResultComposerService,
)
from app.modules.ai_orchestrator.domain.enums import (
    WorkflowModule,
    WorkflowStatus,
    WorkflowStepStatus,
)
from tests.unit.modules.ai_orchestrator.application.fakes import (
    make_definition,
    make_step,
    make_step_result,
)


def _service() -> WorkflowResultComposerService:
    return WorkflowResultComposerService()


class TestComposeStatus:
    def test_all_required_completed_is_completed(self) -> None:
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        results = (make_step_result(WorkflowModule.CLINICAL_NOTE),)

        result = _service().compose(definition, results, 10.0)

        assert result.status is WorkflowStatus.COMPLETED

    def test_required_failure_with_some_success_is_partially_completed(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE),
            make_step(WorkflowModule.SOAP_NOTE),
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE),
            make_step_result(
                WorkflowModule.SOAP_NOTE, status=WorkflowStepStatus.FAILED, summary=None
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.status is WorkflowStatus.PARTIALLY_COMPLETED

    def test_optional_failure_alongside_required_success_is_completed(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE),
            make_step(WorkflowModule.RADIOLOGY_INTERPRETATION, required=False),
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE),
            make_step_result(
                WorkflowModule.RADIOLOGY_INTERPRETATION,
                status=WorkflowStepStatus.FAILED,
                summary=None,
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.status is WorkflowStatus.COMPLETED

    def test_nothing_completed_is_failed(self) -> None:
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        results = (
            make_step_result(
                WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.FAILED, summary=None
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.status is WorkflowStatus.FAILED

    def test_any_cancelled_step_is_cancelled(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.SOAP_NOTE)
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE),
            make_step_result(
                WorkflowModule.SOAP_NOTE, status=WorkflowStepStatus.CANCELLED, summary=None
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.status is WorkflowStatus.CANCELLED

    def test_skipped_steps_alone_do_not_prevent_completed(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE),
            make_step(WorkflowModule.LAB_INTERPRETATION),
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE),
            make_step_result(
                WorkflowModule.LAB_INTERPRETATION,
                status=WorkflowStepStatus.SKIPPED,
                summary=None,
                skipped_reason="no findings",
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.status is WorkflowStatus.COMPLETED


class TestComposeModulesAndDiagnostics:
    def test_executed_modules_are_only_completed_ones(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.SOAP_NOTE)
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE),
            make_step_result(
                WorkflowModule.SOAP_NOTE, status=WorkflowStepStatus.SKIPPED, summary=None
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.executed_modules == (WorkflowModule.CLINICAL_NOTE,)

    def test_skipped_modules_include_skipped_and_cancelled(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE),
            make_step(WorkflowModule.SOAP_NOTE),
            make_step(WorkflowModule.ICD10_CODING),
        )
        results = (
            make_step_result(
                WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.SKIPPED, summary=None
            ),
            make_step_result(
                WorkflowModule.SOAP_NOTE, status=WorkflowStepStatus.CANCELLED, summary=None
            ),
            make_step_result(WorkflowModule.ICD10_CODING),
        )

        result = _service().compose(definition, results, 10.0)

        assert set(result.skipped_modules) == {
            WorkflowModule.CLINICAL_NOTE,
            WorkflowModule.SOAP_NOTE,
        }

    def test_errors_include_module_and_message(self) -> None:
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        results = (
            make_step_result(
                WorkflowModule.CLINICAL_NOTE,
                status=WorkflowStepStatus.FAILED,
                summary=None,
                error_message="provider down",
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert len(result.errors) == 1
        assert "clinical_note" in result.errors[0]
        assert "provider down" in result.errors[0]

    def test_warnings_include_module_and_skipped_reason(self) -> None:
        definition = make_definition(make_step(WorkflowModule.LAB_INTERPRETATION))
        results = (
            make_step_result(
                WorkflowModule.LAB_INTERPRETATION,
                status=WorkflowStepStatus.SKIPPED,
                summary=None,
                skipped_reason="no findings",
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert len(result.warnings) == 1
        assert "lab_interpretation" in result.warnings[0]
        assert "no findings" in result.warnings[0]

    def test_clinical_summary_joins_completed_step_summaries(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.SOAP_NOTE)
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE, summary="note summary"),
            make_step_result(WorkflowModule.SOAP_NOTE, summary="soap summary"),
        )

        result = _service().compose(definition, results, 10.0)

        assert "note summary" in result.clinical_summary
        assert "soap summary" in result.clinical_summary

    def test_clinical_summary_excludes_skipped_and_failed_steps(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.SOAP_NOTE)
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE, summary="note summary"),
            make_step_result(
                WorkflowModule.SOAP_NOTE, status=WorkflowStepStatus.FAILED, summary=None
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.clinical_summary == "note summary"


class TestComposeConfidenceSummary:
    def test_averages_confidence_scores_of_completed_steps(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.LAB_INTERPRETATION),
            make_step(WorkflowModule.RADIOLOGY_INTERPRETATION),
        )
        results = (
            make_step_result(WorkflowModule.LAB_INTERPRETATION, confidence_score=0.8),
            make_step_result(WorkflowModule.RADIOLOGY_INTERPRETATION, confidence_score=0.6),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.confidence_summary == 0.7

    def test_none_when_no_step_reports_confidence(self) -> None:
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        results = (make_step_result(WorkflowModule.CLINICAL_NOTE, confidence_score=None),)

        result = _service().compose(definition, results, 10.0)

        assert result.confidence_summary is None

    def test_skips_none_scores_when_averaging(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE),
            make_step(WorkflowModule.LAB_INTERPRETATION),
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE, confidence_score=None),
            make_step_result(WorkflowModule.LAB_INTERPRETATION, confidence_score=0.9),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.confidence_summary == 0.9

    def test_excludes_non_completed_steps_from_the_average(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE), make_step(WorkflowModule.LAB_INTERPRETATION)
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE, confidence_score=0.5),
            make_step_result(
                WorkflowModule.LAB_INTERPRETATION,
                status=WorkflowStepStatus.FAILED,
                summary=None,
                confidence_score=0.99,
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert result.confidence_summary == 0.5


class TestComposeWorkflowSummary:
    def test_includes_execution_time_and_counts(self) -> None:
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE))
        results = (make_step_result(WorkflowModule.CLINICAL_NOTE),)

        result = _service().compose(definition, results, 250.0)

        assert "1 of 1" in result.workflow_summary
        assert "250ms" in result.workflow_summary

    def test_mentions_failed_count_when_present(self) -> None:
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE, required=False))
        results = (
            make_step_result(
                WorkflowModule.CLINICAL_NOTE, status=WorkflowStepStatus.FAILED, summary=None
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert "failed" in result.workflow_summary

    def test_mentions_skipped_count_when_present(self) -> None:
        definition = make_definition(
            make_step(WorkflowModule.CLINICAL_NOTE),
            make_step(WorkflowModule.LAB_INTERPRETATION),
        )
        results = (
            make_step_result(WorkflowModule.CLINICAL_NOTE),
            make_step_result(
                WorkflowModule.LAB_INTERPRETATION, status=WorkflowStepStatus.SKIPPED, summary=None
            ),
        )

        result = _service().compose(definition, results, 10.0)

        assert "skipped" in result.workflow_summary

    def test_workflow_name_and_step_results_are_preserved(self) -> None:
        definition = make_definition(make_step(WorkflowModule.CLINICAL_NOTE), name="my-workflow")
        results = (make_step_result(WorkflowModule.CLINICAL_NOTE),)

        result = _service().compose(definition, results, 10.0)

        assert result.workflow_name == "my-workflow"
        assert result.step_results == results
        assert result.total_execution_time_ms == 10.0
