"""`EmailAddress` — a shared value object, used across modules (Authentication's
`User`, Organization, Patient, ...). Kept minimal and dependency-free: it
validates *shape* only. Deliverability/MX checks belong to whichever
application-layer flow cares (e.g. a future email-verification use case),
not the value object itself.
"""

import re
from dataclasses import dataclass

from app.shared.domain.exceptions import DomainError
from app.shared.domain.value_object import ValueObject

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidEmailAddressError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value!r} is not a valid email address")


@dataclass(frozen=True, slots=True)
class EmailAddress(ValueObject):
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized or not _EMAIL_PATTERN.match(normalized):
            raise InvalidEmailAddressError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
