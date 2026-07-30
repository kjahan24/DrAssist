"""Domain exceptions for the Patient History module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`DoctorReviewNotFoundError` is defined locally rather than reused from
`app.modules.doctor_review.domain.exceptions` — the same situation every
prior child-document module documents: the owning module exposes no
"not found" error a peer module is allowed to import, so every module
that *references* an existing row by id defines the exception locally.

`ReferenceNotFoundError` backs "Reference validation": the artifact named
by `(reference_type, reference_id)` must actually exist, in its owning
module, and belong to the same clinical encounter as the approving
Doctor Review — see
`application/services/patient_history_reference_validator.py`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class DoctorReviewNotFoundError(DomainError):
    def __init__(self, doctor_review_id: UUID) -> None:
        super().__init__(f"no doctor review found with id {doctor_review_id}")
        self.doctor_review_id = doctor_review_id


class DoctorReviewNotApprovedError(DomainError):
    def __init__(self, doctor_review_id: UUID) -> None:
        super().__init__(
            f"doctor review {doctor_review_id} is not approved; only an approved doctor "
            "review may create patient history"
        )
        self.doctor_review_id = doctor_review_id


class ReferenceNotFoundError(DomainError):
    def __init__(self, reference_type: str, reference_id: UUID) -> None:
        super().__init__(
            f"no {reference_type} record found with id {reference_id} for this encounter"
        )
        self.reference_type = reference_type
        self.reference_id = reference_id


class DuplicatePatientHistoryError(DomainError):
    def __init__(self, reference_type: str, reference_id: UUID) -> None:
        super().__init__(
            f"a patient history record already exists for {reference_type} {reference_id}"
        )
        self.reference_type = reference_type
        self.reference_id = reference_id


class SummaryRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("summary must not be blank")
