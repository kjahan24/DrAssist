"""Domain exceptions for the Diagnosis module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. A
missing referenced `Visit`/`Doctor` raises the *owning* module's own
`PatientVisitNotFoundError`/`DoctorNotFoundError` directly (see
`application/use_cases/record_diagnosis.py`), not a Diagnosis-specific
wrapper — the same cross-module reuse already established by
`app.modules.chief_complaints.application.use_cases.record_chief_complaint.RecordVisitChiefComplaint`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class DiagnosisNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("diagnosis_name must not be blank")


class InvalidSequenceNumberError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"sequence_number must start from 1, got {value}")
        self.value = value


class DuplicateSequenceNumberError(DomainError):
    def __init__(self, visit_id: UUID, sequence_number: int) -> None:
        super().__init__(f"sequence_number {sequence_number} already exists for visit {visit_id}")
        self.visit_id = visit_id
        self.sequence_number = sequence_number


class DuplicatePrimaryDiagnosisError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(f"visit {visit_id} already has a primary diagnosis")
        self.visit_id = visit_id


class PrimaryDiagnosisCannotBeRuledOutError(DomainError):
    def __init__(self) -> None:
        super().__init__("a primary diagnosis cannot be marked as ruled out")
