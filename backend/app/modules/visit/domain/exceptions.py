"""Domain exceptions for the Visit module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. A
missing referenced `Patient`/`Doctor` raises the *owning* module's own
`PatientNotFoundError`/`DoctorNotFoundError` directly (see
`application/use_cases/schedule_visit.py`), not a Visit-specific wrapper —
the same cross-module reuse already established by
`app.modules.patient.application.use_cases.record_patient_allergy.RecordPatientAllergy`
et al.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class VisitNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("visit_number must not be blank")


class DuplicateVisitNumberError(DomainError):
    def __init__(self, organization_id: UUID, visit_number: str) -> None:
        super().__init__(
            f"visit_number {visit_number!r} already exists in organization {organization_id}"
        )
        self.organization_id = organization_id
        self.visit_number = visit_number


class PatientVisitNotFoundError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(f"no patient visit found with id {visit_id}")
        self.visit_id = visit_id


class CheckOutBeforeCheckInError(DomainError):
    def __init__(self) -> None:
        super().__init__("check_out_time must not be before check_in_time")


class ConsultationEndBeforeStartError(DomainError):
    def __init__(self) -> None:
        super().__init__("consultation_end_time must not be before consultation_start_time")


class FollowUpDateRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("follow_up_date is required when follow_up_required is true")


class CompletedVisitCannotReturnToInProgressError(DomainError):
    def __init__(self) -> None:
        super().__init__("a completed visit cannot return to in_progress")
