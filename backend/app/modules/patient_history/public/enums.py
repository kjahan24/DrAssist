"""Public enums — re-exported from the domain layer, not redefined, so
there is exactly one definition of each. Needed at the `public/`
boundary (unlike every prior module in this codebase) because
`PatientHistoryQueryPort.get_by_reference()` takes `ReferenceType` as a
parameter, not only as a DTO field — the first public port in this
codebase whose method signature itself needs an enum type.
"""

from app.modules.patient_history.domain.enums import HistoryType, ReferenceType

__all__ = ["HistoryType", "ReferenceType"]
