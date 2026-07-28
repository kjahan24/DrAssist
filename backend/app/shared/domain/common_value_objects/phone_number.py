"""`PhoneNumber` — a shared value object, used across modules (Patient, and
any future module that collects a contact number). Kept minimal and
dependency-free, mirroring `EmailAddress`: it validates *shape* only
(digit count and allowed characters), not deliverability/carrier lookup.
"""

import re
from dataclasses import dataclass

from app.shared.domain.exceptions import DomainError
from app.shared.domain.value_object import ValueObject

_PHONE_CHARACTERS_PATTERN = re.compile(r"^\+?[0-9()\-.\s]+$")
_MIN_DIGITS = 7
_MAX_DIGITS = 15


class InvalidPhoneNumberError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value!r} is not a valid phone number")


@dataclass(frozen=True, slots=True)
class PhoneNumber(ValueObject):
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        digit_count = len(re.sub(r"\D", "", normalized))
        if (
            not normalized
            or not _PHONE_CHARACTERS_PATTERN.match(normalized)
            or not (_MIN_DIGITS <= digit_count <= _MAX_DIGITS)
        ):
            raise InvalidPhoneNumberError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
