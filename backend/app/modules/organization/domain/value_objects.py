"""Value objects specific to the Organization module.

`EmailAddress` (used by `Organization.email`) is the shared value object —
see `app.shared.domain.common_value_objects.EmailAddress`.
"""

import re
from dataclasses import dataclass

from app.modules.organization.domain.exceptions import InvalidOrganizationCodeError
from app.shared.domain.value_object import ValueObject

_ORGANIZATION_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,31}$")


@dataclass(frozen=True, slots=True)
class OrganizationCode(ValueObject):
    """A short, tenant-facing identifier (distinct from the tenant's UUID
    primary key), e.g. `"ACME-CLINIC"`. Normalized to uppercase so lookups
    are case-insensitive without needing a `CITEXT` column.
    """

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _ORGANIZATION_CODE_PATTERN.match(normalized):
            raise InvalidOrganizationCodeError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
