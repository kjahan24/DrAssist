"""Domain exceptions for the Documents module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`PatientNotFoundError`/`VisitNotFoundError`/`AppointmentNotFoundError` are
defined locally rather than imported from their owning modules — the same
"no module exposes a not-found error a peer is allowed to import" reasoning
`app.modules.appointment.domain.exceptions`'s own docstring documents (none
of `app.modules.patient`, `app.modules.visit`, or `app.modules.appointment`
expose one across the `domain/` boundary; only their `public/` ports are
importable from outside).

Cross-tenant `Patient` access is treated identically to "not found"
(`PatientNotFoundError` covers both) — the same pattern
`app.api.deps.ensure_same_organization` documents. `Visit`/`Appointment`
get a *distinct* ownership-mismatch error instead, because this task's own
Validation section names "Visit ownership"/"Appointment ownership" as their
own checks, separate from mere existence — mirroring
`AppointmentVisitNotFoundError`/`AppointmentVisitMismatchError`'s own split
in `app.modules.appointment.domain.exceptions`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class PatientNotFoundError(DomainError):
    def __init__(self, patient_id: UUID) -> None:
        super().__init__(f"no patient found with id {patient_id}")
        self.patient_id = patient_id


class VisitNotFoundError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(f"no visit found with id {visit_id}")
        self.visit_id = visit_id


class VisitOwnershipMismatchError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(
            f"visit {visit_id} does not belong to the same organization/patient as this document"
        )
        self.visit_id = visit_id


class AppointmentNotFoundError(DomainError):
    def __init__(self, appointment_id: UUID) -> None:
        super().__init__(f"no appointment found with id {appointment_id}")
        self.appointment_id = appointment_id


class AppointmentOwnershipMismatchError(DomainError):
    def __init__(self, appointment_id: UUID) -> None:
        super().__init__(
            f"appointment {appointment_id} does not belong to the same "
            "organization/patient as this document"
        )
        self.appointment_id = appointment_id


class MedicalDocumentNotFoundError(DomainError):
    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"no medical document found with id {document_id}")
        self.document_id = document_id


class TitleRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("title must not be blank")


class OriginalFilenameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("original_filename must not be blank")


class StoredFilenameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("stored_filename must not be blank")


class MimeTypeRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("mime_type must not be blank")


class ExtensionRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("extension must not be blank")


class StoragePathRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("storage_path must not be blank")


class NonPositiveFileSizeError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"file_size_bytes must be greater than zero, got {value}")
        self.value = value


class InvalidSha256ChecksumError(DomainError):
    def __init__(self, value: str) -> None:
        super().__init__(f"{value!r} is not a valid SHA-256 checksum")
        self.value = value


class DuplicateStoredFilenameError(DomainError):
    def __init__(self, stored_filename: str) -> None:
        super().__init__(f"stored_filename {stored_filename!r} is already in use")
        self.stored_filename = stored_filename


class InvalidDocumentStatusTransitionError(DomainError):
    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(f"cannot transition document from {current_status} to {target_status}")
        self.current_status = current_status
        self.target_status = target_status
