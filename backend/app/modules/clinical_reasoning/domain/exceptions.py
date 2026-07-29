"""Domain exceptions for the Clinical Reasoning module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ClinicalNoteNotFoundError` is defined locally rather than reused from
`app.modules.clinical_notes.domain.exceptions` — the same situation
`app.modules.soap_notes.domain.exceptions`/
`app.modules.prescriptions.domain.exceptions`/
`app.modules.lab_orders.domain.exceptions` already document: the Clinical
Notes module never needed a "not found" error of its own, so every
module that *references* an existing `ClinicalNote` by id defines this
exception locally.

Unlike `app.modules.soap_notes.application.use_cases.create_soap_note
.CreateSOAPNote` and `app.modules.prescriptions.application.use_cases
.create_prescription.CreatePrescription` (both of which reuse
`ClinicalNoteNotEditableError` because their own business rules
explicitly tie read-only enforcement to the *parent*'s status), this
module's use cases never check `ClinicalNoteQueryPort.is_editable` — this
task's Business Rules never say "if the linked Clinical Note is
Signed/Locked, Clinical Reasoning becomes read-only" (unlike every prior
Clinical-Note-child module's own task). The only immutability rule this
task states is entirely about `ClinicalReasoning`'s *own* `review_status`
("Approved/Rejected reasoning becomes immutable") — the same "only
encode business rules explicitly stated for the module being built"
reasoning `app.modules.lab_results.domain.exceptions` already documents.
See `domain/entities.py` for the full reasoning.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ClinicalNoteNotFoundError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"no clinical note found with id {clinical_note_id}")
        self.clinical_note_id = clinical_note_id


class ClinicalReasoningNotFoundError(DomainError):
    def __init__(self, clinical_reasoning_id: UUID) -> None:
        super().__init__(f"no clinical reasoning record found with id {clinical_reasoning_id}")
        self.clinical_reasoning_id = clinical_reasoning_id


class ReasoningTextRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("reasoning_text must not be blank")


class ClinicalReasoningNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("approved or rejected clinical reasoning cannot be modified")


class ReviewRequiresPendingStatusError(DomainError):
    def __init__(self) -> None:
        super().__init__("only pending clinical reasoning can be marked as reviewed")
