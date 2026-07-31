"""Unit tests for value objects specific to the Documents module."""

import pytest

from app.modules.documents.domain.exceptions import InvalidSha256ChecksumError
from app.modules.documents.domain.value_objects import Sha256Checksum

_VALID_HEX_64 = "a" * 64


class TestSha256Checksum:
    def test_accepts_a_valid_64_character_hex_string(self) -> None:
        checksum = Sha256Checksum(_VALID_HEX_64)
        assert str(checksum) == _VALID_HEX_64

    def test_normalizes_to_lowercase(self) -> None:
        checksum = Sha256Checksum("A" * 64)
        assert str(checksum) == "a" * 64

    def test_strips_surrounding_whitespace(self) -> None:
        checksum = Sha256Checksum(f"  {_VALID_HEX_64}  ")
        assert str(checksum) == _VALID_HEX_64

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "a" * 63,
            "a" * 65,
            "g" * 64,
            "not-a-checksum",
        ],
    )
    def test_rejects_invalid_checksums(self, raw: str) -> None:
        with pytest.raises(InvalidSha256ChecksumError):
            Sha256Checksum(raw)

    def test_equality_is_by_value(self) -> None:
        assert Sha256Checksum(_VALID_HEX_64) == Sha256Checksum(_VALID_HEX_64.upper())
        assert Sha256Checksum("a" * 64) != Sha256Checksum("b" * 64)
