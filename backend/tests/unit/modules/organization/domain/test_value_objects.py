"""Unit tests for value objects used by the Organization module."""

import pytest

from app.modules.organization.domain.exceptions import InvalidOrganizationCodeError
from app.modules.organization.domain.value_objects import OrganizationCode


class TestOrganizationCode:
    def test_valid_code_is_accepted(self) -> None:
        assert str(OrganizationCode("acme-clinic")) == "ACME-CLINIC"

    def test_normalizes_to_uppercase(self) -> None:
        assert str(OrganizationCode("Acme_Clinic1")) == "ACME_CLINIC1"

    def test_whitespace_is_stripped(self) -> None:
        assert str(OrganizationCode("  ACME  ")) == "ACME"

    def test_equality_is_by_normalized_value(self) -> None:
        assert OrganizationCode("acme") == OrganizationCode("ACME")

    @pytest.mark.parametrize(
        "value", ["", "A", "-STARTS-WITH-DASH", "HAS SPACE", "HAS@SYMBOL", "x" * 33]
    )
    def test_invalid_codes_are_rejected(self, value: str) -> None:
        with pytest.raises(InvalidOrganizationCodeError):
            OrganizationCode(value)
