"""Unit tests for `PhoneNumber` — see
`tests.unit.modules.authentication.domain.test_value_objects` for
`EmailAddress`'s existing coverage (introduced there first; not
duplicated here)."""

import pytest

from app.shared.domain.common_value_objects import PhoneNumber
from app.shared.domain.common_value_objects.phone_number import InvalidPhoneNumberError


class TestPhoneNumber:
    @pytest.mark.parametrize(
        "raw",
        [
            "+1 555 010 0100",
            "555-0100-100",
            "(555) 010-0100",
            "+919876543210",
            "1234567",
        ],
    )
    def test_accepts_valid_phone_numbers(self, raw: str) -> None:
        assert str(PhoneNumber(raw)) == raw.strip()

    def test_strips_surrounding_whitespace(self) -> None:
        assert str(PhoneNumber("  +1 555 0100  ")) == "+1 555 0100"

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "12345",
            "1234567890123456",
            "not-a-phone-number",
            "555-0100x123",
        ],
    )
    def test_rejects_invalid_phone_numbers(self, raw: str) -> None:
        with pytest.raises(InvalidPhoneNumberError):
            PhoneNumber(raw)

    def test_equality_is_by_value(self) -> None:
        assert PhoneNumber("+1 555 0100") == PhoneNumber("+1 555 0100")
        assert PhoneNumber("+1 555 0100") != PhoneNumber("+1 555 0101")
