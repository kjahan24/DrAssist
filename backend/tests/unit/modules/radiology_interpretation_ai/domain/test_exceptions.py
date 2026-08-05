"""Unit tests for the AI Radiology Interpretation module's domain
exceptions."""

from app.modules.radiology_interpretation_ai.domain.exceptions import (
    DuplicateRadiologyFindingError,
    EmptyRadiologyReportError,
    HallucinatedRadiologyFindingError,
    InconsistentRadiologyRecommendationsError,
    InvalidRadiologyConfidenceValueError,
    InvalidRadiologyInterpretationInputError,
    InvalidRadiologyInterpretationResponseFormatError,
    MalformedRadiologyReportError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidRadiologyInterpretationInputError:
    def test_carries_the_reason(self) -> None:
        error = InvalidRadiologyInterpretationInputError("language must not be blank")
        assert error.reason == "language must not be blank"
        assert "language must not be blank" in str(error)
        assert isinstance(error, DomainError)


class TestEmptyRadiologyReportError:
    def test_is_a_domain_error(self) -> None:
        error = EmptyRadiologyReportError()
        assert isinstance(error, DomainError)
        assert "must not be empty" in str(error)


class TestMalformedRadiologyReportError:
    def test_carries_the_reason(self) -> None:
        error = MalformedRadiologyReportError("too short")
        assert error.reason == "too short"


class TestInvalidRadiologyInterpretationResponseFormatError:
    def test_carries_the_reason(self) -> None:
        error = InvalidRadiologyInterpretationResponseFormatError("not valid JSON")
        assert error.reason == "not valid JSON"


class TestDuplicateRadiologyFindingError:
    def test_carries_the_description(self) -> None:
        error = DuplicateRadiologyFindingError("Pneumothorax")
        assert error.description == "Pneumothorax"
        assert "Pneumothorax" in str(error)


class TestHallucinatedRadiologyFindingError:
    def test_carries_the_field_name_and_placeholder(self) -> None:
        error = HallucinatedRadiologyFindingError("examination_summary", "[insert]")
        assert error.field_name == "examination_summary"
        assert error.placeholder == "[insert]"


class TestInconsistentRadiologyRecommendationsError:
    def test_carries_the_list_name_and_item(self) -> None:
        error = InconsistentRadiologyRecommendationsError(
            "suggested_follow_up_imaging", "Repeat CT"
        )
        assert error.list_name == "suggested_follow_up_imaging"
        assert error.item == "Repeat CT"


class TestInvalidRadiologyConfidenceValueError:
    def test_is_a_domain_error(self) -> None:
        error = InvalidRadiologyConfidenceValueError()
        assert isinstance(error, DomainError)
        assert "confidence_score" in str(error)
