"""Domain exceptions for the Chief Complaints module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. A
missing referenced `Visit`/`Doctor` raises the *owning* module's own
`PatientVisitNotFoundError`/`DoctorNotFoundError` directly (see
`application/use_cases/record_chief_complaint.py`), not a
Chief-Complaints-specific wrapper — the same cross-module reuse already
established by
`app.modules.vital_signs.application.use_cases.record_vital_signs.RecordVisitVitalSigns`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ComplaintRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("complaint must not be blank")


class InvalidSequenceNumberError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"sequence_number must start from 1, got {value}")
        self.value = value


class DuplicateSequenceNumberError(DomainError):
    def __init__(self, visit_id: UUID, sequence_number: int) -> None:
        super().__init__(f"sequence_number {sequence_number} already exists for visit {visit_id}")
        self.visit_id = visit_id
        self.sequence_number = sequence_number


class NegativeDurationValueError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"duration_value must not be negative, got {value}")
        self.value = value


class DurationUnitRequiresDurationValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("duration_unit is only allowed when duration_value is provided")
