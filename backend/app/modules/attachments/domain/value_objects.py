"""Value objects specific to the Attachments module.

`Sha256Checksum` validates *shape* only — exactly 64 hexadecimal
characters, the fixed, unambiguous length of a SHA-256 digest — the same
"module-local value object with its own format" pattern
`app.modules.patient.domain.value_objects.ICD10Code` established. Unlike
`icd10_code` in `app.modules.diagnosis.domain.entities` (deliberately left
unvalidated because no format was specified), this format isn't an
invented business rule: "a SHA-256 checksum" *means* 64 hex characters by
definition, so validating it is validating the field's own name, not
guessing at an unstated constraint.
"""

import re
from dataclasses import dataclass

from app.modules.attachments.domain.exceptions import InvalidSha256ChecksumError
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
