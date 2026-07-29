"""Domain exceptions for the SOAP Notes module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ClinicalNoteNotFoundError` is defined locally rather than reused from
`app.modules.clinical_notes.domain.exceptions` — unlike
`PatientVisitNotFoundError`/`DoctorNotFoundError` (which every prior
Visit sub-module reuses directly, since Visit/Doctor use cases had
already needed one), the Clinical Notes module never needed a "not
found" error of its own: its own use case only ever *creates* a clinical
note, never looks up an existing one. This module is the first consumer
to *reference* an existing `ClinicalNote` by id, so it defines the
exception the owning module happens not to have — the same reuse
*pattern*, applied to a module that hadn't needed it yet.

`ClinicalNoteNotEditableError` (the read-only enforcement error) *is*
reused directly from `app.modules.clinical_notes.domain.exceptions` —
see `application/use_cases/create_soap_note.py`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ClinicalNoteNotFoundError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"no clinical note found with id {clinical_note_id}")
        self.clinical_note_id = clinical_note_id


class DuplicateSOAPNoteError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"clinical note {clinical_note_id} already has a SOAP note")
        self.clinical_note_id = clinical_note_id


class SOAPNoteNotFoundError(DomainError):
    def __init__(self, soap_note_id: UUID) -> None:
        super().__init__(f"no SOAP note found with id {soap_note_id}")
        self.soap_note_id = soap_note_id
