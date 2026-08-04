"""Unit tests for the AI Lab Interpretation module's domain exceptions."""

from app.modules.lab_interpretation_ai.domain.exceptions import (
    DuplicateLabValueError,
    HallucinatedLabValueError,
    ImpossibleLabValueRangeError,
    InvalidLabInterpretationInputError,
    InvalidLabInterpretationResponseFormatError,
    InvalidLabUnitError,
    MalformedLabValueError,
    MissingLabReasoningError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidLabInterpretationInputError:
    def test_carries_the_reason(self) -> None:
        error = InvalidLabInterpretationInputError("lab_values must not be empty")
        assert error.reason == "lab_values must not be empty"
        assert "lab_values must not be empty" in str(error)
        assert isinstance(error, DomainError)


class TestMalformedLabValueError:
    def test_carries_the_reason(self) -> None:
        error = MalformedLabValueError("test_name must not be blank")
        assert error.reason == "test_name must not be blank"
        assert isinstance(error, DomainError)


class TestDuplicateLabValueError:
    def test_carries_the_test_name(self) -> None:
        error = DuplicateLabValueError("Potassium")
        assert error.test_name == "Potassium"
        assert "Potassium" in str(error)


class TestImpossibleLabValueRangeError:
    def test_carries_the_test_name(self) -> None:
        error = ImpossibleLabValueRangeError("Potassium")
        assert error.test_name == "Potassium"


class TestInvalidLabUnitError:
    def test_carries_the_test_name(self) -> None:
        error = InvalidLabUnitError("Potassium")
        assert error.test_name == "Potassium"


class TestInvalidLabInterpretationResponseFormatError:
    def test_carries_the_reason(self) -> None:
        error = InvalidLabInterpretationResponseFormatError("not valid JSON")
        assert error.reason == "not valid JSON"


class TestMissingLabReasoningError:
    def test_carries_the_reason(self) -> None:
        error = MissingLabReasoningError("overall_interpretation must not be blank")
        assert error.reason == "overall_interpretation must not be blank"


class TestHallucinatedLabValueError:
    def test_carries_the_field_name_and_placeholder(self) -> None:
        error = HallucinatedLabValueError("overall_interpretation", "[insert]")
        assert error.field_name == "overall_interpretation"
        assert error.placeholder == "[insert]"
