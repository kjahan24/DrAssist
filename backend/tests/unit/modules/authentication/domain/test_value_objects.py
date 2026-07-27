"""Unit tests for value objects used by the Authentication module."""

import pytest

from app.modules.authentication.domain.exceptions import InvalidPermissionCodeError
from app.modules.authentication.domain.value_objects import (
    HashedPassword,
    InvalidHashedPasswordError,
    PermissionCode,
)
from app.shared.domain.common_value_objects.email_address import (
    EmailAddress,
    InvalidEmailAddressError,
)


class TestEmailAddress:
    def test_valid_email_is_accepted(self) -> None:
        assert str(EmailAddress("Doctor@Example.com")) == "doctor@example.com"

    def test_whitespace_is_stripped(self) -> None:
        assert str(EmailAddress("  a@b.com  ")) == "a@b.com"

    @pytest.mark.parametrize("value", ["not-an-email", "missing-domain@", "@missing-local.com", ""])
    def test_invalid_values_are_rejected(self, value: str) -> None:
        with pytest.raises(InvalidEmailAddressError):
            EmailAddress(value)

    def test_is_immutable(self) -> None:
        email = EmailAddress("a@b.com")
        with pytest.raises(AttributeError):
            email.value = "other@b.com"  # type: ignore[misc]

    def test_equality_is_by_value(self) -> None:
        assert EmailAddress("a@b.com") == EmailAddress("A@B.com")


class TestHashedPassword:
    def test_accepts_a_bcrypt_looking_hash(self) -> None:
        value = "$2b$12$" + "x" * 53
        assert HashedPassword(value).value == value

    @pytest.mark.parametrize(
        "value", ["plaintext-password", "", "md5:abc123", "$argon2id$v=19$..."]
    )
    def test_rejects_values_that_dont_look_like_bcrypt(self, value: str) -> None:
        with pytest.raises(InvalidHashedPasswordError):
            HashedPassword(value)


class TestPermissionCode:
    def test_valid_module_dot_action_is_accepted(self) -> None:
        assert str(PermissionCode("patients.read")) == "patients.read"

    def test_is_normalized_to_lowercase(self) -> None:
        assert str(PermissionCode("Patients.Read")) == "patients.read"

    @pytest.mark.parametrize(
        "value", ["patients", "patients.", ".read", "patients read", "patients..read", ""]
    )
    def test_malformed_codes_are_rejected(self, value: str) -> None:
        with pytest.raises(InvalidPermissionCodeError):
            PermissionCode(value)
