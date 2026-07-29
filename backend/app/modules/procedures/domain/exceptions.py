"""Domain exceptions for the Procedures module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. A
missing referenced `Visit`/`Doctor` raises the *owning* module's own
`PatientVisitNotFoundError`/`DoctorNotFoundError` directly (see
`application/use_cases/record_procedure.py`), not a Procedures-specific
wrapper — the same cross-module reuse already established by
`app.modules.diagnosis.application.use_cases.record_diagnosis.RecordVisitDiagnosis`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ProcedureNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("procedure_name must not be blank")


class InvalidSequenceNumberError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"sequence_number must start from 1, got {value}")
        self.value = value


class DuplicateSequenceNumberError(DomainError):
    def __init__(self, visit_id: UUID, sequence_number: int) -> None:
        super().__init__(f"sequence_number {sequence_number} already exists for visit {visit_id}")
        self.visit_id = visit_id
        self.sequence_number = sequence_number


class PerformedAtRequiredForCompletedProcedureError(DomainError):
    def __init__(self) -> None:
        super().__init__("performed_at is required when procedure_status is completed")


class CancelledProcedureCannotHavePerformedAtError(DomainError):
    def __init__(self) -> None:
        super().__init__("a cancelled procedure cannot have performed_at")
