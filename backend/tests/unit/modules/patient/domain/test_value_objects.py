"""Unit tests for value objects specific to the Patient module."""

import pytest

from app.modules.patient.domain.exceptions import InvalidICD10CodeError
from app.modules.patient.domain.value_objects import ICD10Code


class TestICD10Code:
    @pytest.mark.parametrize(
        "raw",
        [
            "E11.9",
            "J45",
            "S72.001A",
            "A00",
            "Z99.89",
        ],
    )
    def test_accepts_valid_codes(self, raw: str) -> None:
        assert str(ICD10Code(raw)) == raw.upper()

    def test_normalizes_to_uppercase(self) -> None:
        assert str(ICD10Code("e11.9")) == "E11.9"

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(ICD10Code("  E11.9  ")) == "E11.9"

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "11.9",
            "EE1.9",
            "E1",
            "E11.99999",
            "not-a-code",
        ],
    )
    def test_rejects_invalid_codes(self, raw: str) -> None:
        with pytest.raises(InvalidICD10CodeError):
            ICD10Code(raw)

    def test_equality_is_by_value(self) -> None:
        assert ICD10Code("E11.9") == ICD10Code("e11.9")
        assert ICD10Code("E11.9") != ICD10Code("E11.8")
