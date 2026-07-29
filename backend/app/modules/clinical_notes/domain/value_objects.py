"""Value objects specific to the Clinical Notes module.

`Signature` bundles `signed_at`/`signed_by` together (rather than two
independently-nullable fields on `ClinicalNote`) because the business
rules state both exist *together* — "signed_at exists only when
status = Signed or Locked" and "signed_by exists only when status =
Signed or Locked" describe one indivisible fact ("this note has been
signed, by whom, and when"), not two coincidentally-related fields. This
is the same "guarantee a mutual invariant" justification
`app.modules.vital_signs.domain.value_objects.BloodPressure` documents —
though unlike `BloodPressure`, `Signature` has no internal cross-field
rule of its own to validate; its value is structural: `ClinicalNote.
signature` is typed `Signature | None`, so "signed_by without signed_at"
(or vice versa) cannot be represented in memory at all, not merely
rejected at construction time.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class Signature(ValueObject):
    signed_at: datetime
    signed_by: UUID
