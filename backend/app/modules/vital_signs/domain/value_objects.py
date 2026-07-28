"""Value objects specific to the Vital Signs module.

`BloodPressure` bundles `systolic`/`diastolic` together (rather than two
independent `int` fields on `VisitVitalSigns`) because "systolic must be
greater than diastolic" is a *relational* invariant between the two
values — encapsulating them in one value object means an invalid reading
can never exist in memory, the same Tier 3 validation guarantee
`app.shared.domain.value_object.ValueObject` documents. This is the
module's first multi-field value object; every other value object in the
codebase so far (`EmailAddress`, `PhoneNumber`, `ICD10Code`, ...) wraps a
single primitive.
"""

from dataclasses import dataclass

from app.modules.vital_signs.domain.exceptions import InvalidBloodPressureError
from app.shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class BloodPressure(ValueObject):
    systolic: int
    diastolic: int

    def __post_init__(self) -> None:
        if self.systolic <= self.diastolic:
            raise InvalidBloodPressureError(self.systolic, self.diastolic)

    def __str__(self) -> str:
        return f"{self.systolic}/{self.diastolic}"
