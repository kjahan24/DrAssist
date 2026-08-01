"""Unit tests for value objects specific to the Family / Caregiver Access
module."""

import pytest

from app.modules.family_access.domain.exceptions import InvalidInvitationTokenHashError
from app.modules.family_access.domain.value_objects import InvitationTokenHash

_VALID_HEX_64 = "a" * 64


class TestInvitationTokenHash:
    def test_accepts_a_valid_64_character_hex_string(self) -> None:
        token_hash = InvitationTokenHash(_VALID_HEX_64)
        assert str(token_hash) == _VALID_HEX_64

    def test_normalizes_to_lowercase(self) -> None:
        token_hash = InvitationTokenHash("A" * 64)
        assert str(token_hash) == "a" * 64

    def test_strips_surrounding_whitespace(self) -> None:
        token_hash = InvitationTokenHash(f"  {_VALID_HEX_64}  ")
        assert str(token_hash) == _VALID_HEX_64

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "a" * 63,
            "a" * 65,
            "g" * 64,
            "not-a-token-hash",
        ],
    )
    def test_rejects_invalid_hashes(self, raw: str) -> None:
        with pytest.raises(InvalidInvitationTokenHashError):
            InvitationTokenHash(raw)

    def test_equality_is_by_value(self) -> None:
        assert InvitationTokenHash(_VALID_HEX_64) == InvitationTokenHash(_VALID_HEX_64.upper())
        assert InvitationTokenHash("a" * 64) != InvitationTokenHash("b" * 64)
