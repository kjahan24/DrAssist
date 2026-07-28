"""Value objects specific to the Patient module.

`EmailAddress`/`PhoneNumber` (used by `Patient`, `PatientContact`,
`EmergencyContact`) are the shared value objects — see
`app.shared.domain.common_value_objects`. `ICD10Code` is kept local to
this module (not promoted to the shared kernel) since it's only used by
`PatientMedicalCondition.icd10_code` today — see
`app.modules.organization.domain.value_objects.OrganizationCode` for the
identical "module-local value object with its own format" pattern this
follows.
"""

import re
from dataclasses import dataclass

from app.modules.patient.domain.exceptions import InvalidICD10CodeError
from app.shared.domain.value_object import ValueObject

_ICD10_PATTERN = re.compile(r"^[A-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})?$")


@dataclass(frozen=True, slots=True)
class ICD10Code(ValueObject):
    """An ICD-10-CM diagnosis code, e.g. `"E11.9"` (type 2 diabetes) or
    `"J45"` (asthma). Normalized to uppercase so lookups/comparisons are
    case-insensitive; validates *shape* only (the category letter + digit
    + alphanumeric, optionally followed by a decimal point and up to four
    more alphanumeric characters), not membership in the actual published
    ICD-10-CM code list.
    """

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _ICD10_PATTERN.match(normalized):
            raise InvalidICD10CodeError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
