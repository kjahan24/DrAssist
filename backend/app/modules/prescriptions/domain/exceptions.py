"""Domain exceptions for the Prescription module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ClinicalNoteNotFoundError` is defined locally rather than reused from
`app.modules.clinical_notes.domain.exceptions` — the same situation
`app.modules.soap_notes.domain.exceptions` already documents: the
Clinical Notes module never needed a "not found" error of its own (its
own use case only ever *creates* a clinical note), so every module that
*references* an existing `ClinicalNote` by id defines this exception
locally.

`ClinicalNoteNotEditableError` (the read-only enforcement error for
"if the linked Clinical Note is Signed or Locked") *is* reused directly
from `app.modules.clinical_notes.domain.exceptions` — see
`application/use_cases/create_prescription.py`. It is distinct from
`PrescriptionNotEditableError` below, which protects this module's *own*
Draft/Final status instead.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ClinicalNoteNotFoundError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"no clinical note found with id {clinical_note_id}")
        self.clinical_note_id = clinical_note_id


class DuplicatePrescriptionError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"clinical note {clinical_note_id} already has a prescription")
        self.clinical_note_id = clinical_note_id


class PrescriptionNotFoundError(DomainError):
    def __init__(self, prescription_id: UUID) -> None:
        super().__init__(f"no prescription found with id {prescription_id}")
        self.prescription_id = prescription_id


class PrescriptionNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("prescription_number must not be blank")


class DuplicatePrescriptionNumberError(DomainError):
    def __init__(self, prescription_number: str) -> None:
        super().__init__(f"prescription_number {prescription_number!r} is already in use")
        self.prescription_number = prescription_number


class PrescriptionNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("only a draft prescription can be modified")


class PrescriptionRequiresAtLeastOneItemError(DomainError):
    def __init__(self, prescription_id: UUID) -> None:
        super().__init__(
            f"prescription {prescription_id} must contain at least one item before it can "
            "be finalized"
        )
        self.prescription_id = prescription_id


class MedicationNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("medication_name must not be blank")
