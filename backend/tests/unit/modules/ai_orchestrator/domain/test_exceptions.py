"""Tests for the AI Healthcare Orchestrator module's domain exceptions
— message content and attribute preservation."""

from app.modules.ai_orchestrator.domain.exceptions import (
    CircularDependencyError,
    DuplicateModuleExecutionError,
    InvalidWorkflowExecutionInputError,
    InvalidWorkflowGraphError,
    MissingModuleOutputError,
    MissingPrerequisiteError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidWorkflowExecutionInputError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidWorkflowExecutionInputError("bad"), DomainError)

    def test_message_includes_reason(self) -> None:
        error = InvalidWorkflowExecutionInputError("chief_complaint must not be blank")
        assert "chief_complaint must not be blank" in str(error)

    def test_stores_reason_attribute(self) -> None:
        error = InvalidWorkflowExecutionInputError("bad")
        assert error.reason == "bad"


class TestInvalidWorkflowGraphError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidWorkflowGraphError("bad"), DomainError)

    def test_message_includes_reason(self) -> None:
        error = InvalidWorkflowGraphError("dangling dependency")
        assert "dangling dependency" in str(error)

    def test_stores_reason_attribute(self) -> None:
        error = InvalidWorkflowGraphError("bad")
        assert error.reason == "bad"


class TestCircularDependencyError:
    def test_is_domain_error(self) -> None:
        assert isinstance(CircularDependencyError(("a", "b", "a")), DomainError)

    def test_message_includes_cycle(self) -> None:
        error = CircularDependencyError(("a", "b", "a"))
        assert "a -> b -> a" in str(error)

    def test_stores_cycle_attribute(self) -> None:
        error = CircularDependencyError(("a", "b", "a"))
        assert error.cycle == ("a", "b", "a")


class TestDuplicateModuleExecutionError:
    def test_is_domain_error(self) -> None:
        assert isinstance(DuplicateModuleExecutionError("clinical_note"), DomainError)

    def test_message_includes_module(self) -> None:
        error = DuplicateModuleExecutionError("clinical_note")
        assert "clinical_note" in str(error)

    def test_stores_module_attribute(self) -> None:
        error = DuplicateModuleExecutionError("clinical_note")
        assert error.module == "clinical_note"


class TestMissingPrerequisiteError:
    def test_is_domain_error(self) -> None:
        assert isinstance(
            MissingPrerequisiteError("lab_interpretation", "no findings"), DomainError
        )

    def test_message_includes_module_and_reason(self) -> None:
        error = MissingPrerequisiteError("lab_interpretation", "no findings")
        assert "lab_interpretation" in str(error)
        assert "no findings" in str(error)

    def test_stores_attributes(self) -> None:
        error = MissingPrerequisiteError("lab_interpretation", "no findings")
        assert error.module == "lab_interpretation"
        assert error.reason == "no findings"


class TestMissingModuleOutputError:
    def test_is_domain_error(self) -> None:
        error = MissingModuleOutputError("soap_note", "clinical_note")
        assert isinstance(error, DomainError)

    def test_message_includes_module_and_dependency(self) -> None:
        error = MissingModuleOutputError("soap_note", "clinical_note")
        assert "soap_note" in str(error)
        assert "clinical_note" in str(error)

    def test_stores_attributes(self) -> None:
        error = MissingModuleOutputError("soap_note", "clinical_note")
        assert error.module == "soap_note"
        assert error.dependency == "clinical_note"
