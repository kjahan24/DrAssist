"""Domain exceptions for the Clinical Notes module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`. A
missing referenced `Visit`/`Doctor` raises the *owning* module's own
`PatientVisitNotFoundError`/`DoctorNotFoundError` directly (see
`application/use_cases/create_clinical_note.py`), not a
ClinicalNotes-specific wrapper — the same cross-module reuse already
established by
`app.modules.attachments.application.use_cases.upload_attachment.UploadVisitAttachment`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class NoteNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("note_number must not be blank")


class DuplicateNoteNumberError(DomainError):
    def __init__(self, note_number: str) -> None:
        super().__init__(f"note_number {note_number!r} is already in use")
        self.note_number = note_number


class VisitPatientMismatchError(DomainError):
    def __init__(self, visit_id: UUID, patient_id: UUID) -> None:
        super().__init__(f"visit {visit_id} does not belong to patient {patient_id}")
        self.visit_id = visit_id
        self.patient_id = patient_id


class ClinicalNoteNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("only a draft clinical note can be modified")


class LockRequiresSignedNoteError(DomainError):
    def __init__(self) -> None:
        super().__init__("a clinical note must be signed before it can be locked")


class SignatureRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("a signed or locked clinical note must have a signature")


class SignatureNotAllowedError(DomainError):
    def __init__(self) -> None:
        super().__init__("only a signed or locked clinical note may have a signature")


class LockedAtRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("a locked clinical note must have locked_at set")


class LockedAtNotAllowedError(DomainError):
    def __init__(self) -> None:
        super().__init__("only a locked clinical note may have locked_at set")
