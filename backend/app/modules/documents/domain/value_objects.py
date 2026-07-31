"""Value objects specific to the Documents module.

`Sha256Checksum` validates *shape* only — exactly 64 hexadecimal
characters, the fixed, unambiguous length of a SHA-256 digest. This is a
module-local duplicate of `app.modules.attachments.domain.value_objects
.Sha256Checksum` rather than an import of it: domain code never imports
across module boundaries (see that module's own entity docstring), so
each module that needs this exact format constraint defines its own copy
— the same "per-module value object with its own format" pattern
`app.modules.patient.domain.value_objects.ICD10Code` and
`app.modules.organization.domain.value_objects.OrganizationCode` already
establish. Promoting it to `app.shared.domain.common_value_objects`
would be the natural next step if a *third* module needed it, but doing
so now would mean modifying the Attachments module without an
established need (rule: never modify a previous module unless
absolutely necessary).
"""

import re
from dataclasses import dataclass

from app.modules.documents.domain.exceptions import InvalidSha256ChecksumError
from app.shared.domain.value_object import ValueObject

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Sha256Checksum(ValueObject):
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _SHA256_PATTERN.match(normalized):
            raise InvalidSha256ChecksumError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
