"""Unit tests for the AI Pathology Interpretation module's domain
exceptions."""

from app.modules.pathology_interpretation_ai.domain.exceptions import (
    DuplicatePathologyFindingError,
    EmptyPathologyReportError,
    HallucinatedPathologyFindingError,
    InconsistentPathologyConclusionsError,
    InvalidPathologyConfidenceValueError,
    InvalidPathologyInterpretationInputError,
    InvalidPathologyInterpretationResponseFormatError,
    MalformedPathologyReportError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidPathologyInterpretationInputError:
    def test_carries_the_reason(self) -> None:
        error = InvalidPathologyInterpretationInputError("language must not be blank")
        assert error.reason == "language must not be blank"
        assert "language must not be blank" in str(error)
        assert isinstance(error, DomainError)


class TestEmptyPathologyReportError:
    def test_is_a_domain_error(self) -> None:
        error = EmptyPathologyReportError()
        assert isinstance(error, DomainError)
        assert "must not be empty" in str(error)


class TestMalformedPathologyReportError:
    def test_carries_the_reason(self) -> None:
        error = MalformedPathologyReportError("too short")
        assert error.reason == "too short"


class TestInvalidPathologyInterpretationResponseFormatError:
    def test_carries_the_reason(self) -> None:
        error = InvalidPathologyInterpretationResponseFormatError("not valid JSON")
        assert error.reason == "not valid JSON"


class TestDuplicatePathologyFindingError:
    def test_carries_the_description(self) -> None:
        error = DuplicatePathologyFindingError("Invasive ductal carcinoma")
        assert error.description == "Invasive ductal carcinoma"
        assert "Invasive ductal carcinoma" in str(error)


class TestHallucinatedPathologyFindingError:
    def test_carries_the_field_name_and_placeholder(self) -> None:
        error = HallucinatedPathologyFindingError("pathology_summary", "[insert]")
        assert error.field_name == "pathology_summary"
        assert error.placeholder == "[insert]"


class TestInconsistentPathologyConclusionsError:
    def test_carries_the_list_name_and_item(self) -> None:
        error = InconsistentPathologyConclusionsError("suggested_follow_up", "Repeat biopsy")
        assert error.list_name == "suggested_follow_up"
        assert error.item == "Repeat biopsy"


class TestInvalidPathologyConfidenceValueError:
    def test_is_a_domain_error(self) -> None:
        error = InvalidPathologyConfidenceValueError()
        assert isinstance(error, DomainError)
        assert "confidence_score" in str(error)
