"""Domain exceptions for the Doctor Review module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ClinicalNoteNotFoundError` is defined locally rather than reused from
`app.modules.clinical_notes.domain.exceptions` — the same situation every
prior child-document module documents: the owning module exposes no
"not found" error a peer module is allowed to import, so every module
that *references* an existing row by id defines the exception locally.

`ApprovedCategoryMissingRecordError` backs "Cross-module consistency":
a doctor cannot mark a documentation category (SOAP Note, Prescription,
Lab Orders, Lab Results, Clinical Reasoning, Differential Diagnosis,
ICD-10 Coding) as approved if no record of that category exists for the
linked Clinical Note — see
`application/services/doctor_review_consistency_service.py`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ClinicalNoteNotFoundError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"no clinical note found with id {clinical_note_id}")
        self.clinical_note_id = clinical_note_id


class DoctorReviewNotFoundError(DomainError):
    def __init__(self, doctor_review_id: UUID) -> None:
        super().__init__(f"no doctor review found with id {doctor_review_id}")
        self.doctor_review_id = doctor_review_id


class DuplicateDoctorReviewError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"clinical note {clinical_note_id} already has a doctor review")
        self.clinical_note_id = clinical_note_id


class DoctorReviewNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("approved or rejected doctor review cannot be modified")


class InvalidReviewStatusTransitionError(DomainError):
    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"cannot transition doctor review from {current_status} to {target_status}"
        )
        self.current_status = current_status
        self.target_status = target_status


class ApprovedCategoryMissingRecordError(DomainError):
    def __init__(self, category: str, clinical_note_id: UUID) -> None:
        super().__init__(
            f"cannot mark {category!r} as approved: no {category} record exists for "
            f"clinical note {clinical_note_id}"
        )
        self.category = category
        self.clinical_note_id = clinical_note_id
