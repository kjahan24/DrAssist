"""Domain exceptions for the Differential Diagnosis module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ClinicalNoteNotFoundError` and `ClinicalReasoningNotFoundError` are
defined locally rather than reused from
`app.modules.clinical_notes.domain.exceptions`/
`app.modules.clinical_reasoning.domain.exceptions` — the same situation
every prior child-document module documents: neither owning module
exposes a "not found" error a peer module is allowed to import, so every
module that *references* an existing row by id defines the exception
locally.

Unlike `app.modules.soap_notes.application.use_cases.create_soap_note
.CreateSOAPNote`/`app.modules.prescriptions.application.use_cases
.create_prescription.CreatePrescription` (both of which reuse
`ClinicalNoteNotEditableError` because their own business rules
explicitly tie read-only enforcement to the *parent*'s status), this
module's use cases never check `ClinicalNoteQueryPort.is_editable` or
`ClinicalReasoningQueryPort.is_editable` — this task's Business Rules
never say "if the linked Clinical Note/Clinical Reasoning is X, this
becomes read-only". The only immutability rule stated is entirely about
this aggregate's *own* `review_status` ("Approved and Rejected diagnoses
become read-only") — the same "only encode business rules explicitly
stated for the module being built" reasoning
`app.modules.clinical_reasoning.domain.exceptions` already establishes.
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


class ClinicalReasoningClinicalNoteMismatchError(DomainError):
    def __init__(self, clinical_reasoning_id: UUID, clinical_note_id: UUID) -> None:
        super().__init__(
            f"clinical reasoning {clinical_reasoning_id} does not belong to clinical note "
            f"{clinical_note_id}"
        )
        self.clinical_reasoning_id = clinical_reasoning_id
        self.clinical_note_id = clinical_note_id


class DifferentialDiagnosisNotFoundError(DomainError):
    def __init__(self, differential_diagnosis_id: UUID) -> None:
        super().__init__(f"no differential diagnosis found with id {differential_diagnosis_id}")
        self.differential_diagnosis_id = differential_diagnosis_id


class DiagnosisNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("diagnosis_name must not be blank")


class InvalidRankingError(DomainError):
    def __init__(self, value: int) -> None:
        super().__init__(f"ranking must start from 1, got {value}")
        self.value = value


class DuplicateRankingError(DomainError):
    def __init__(self, clinical_note_id: UUID, ranking: int) -> None:
        super().__init__(f"ranking {ranking} already exists for clinical note {clinical_note_id}")
        self.clinical_note_id = clinical_note_id
        self.ranking = ranking


class DuplicateDiagnosisNameError(DomainError):
    def __init__(self, clinical_note_id: UUID, diagnosis_name: str) -> None:
        super().__init__(
            f"diagnosis_name {diagnosis_name!r} already exists for clinical note "
            f"{clinical_note_id}"
        )
        self.clinical_note_id = clinical_note_id
        self.diagnosis_name = diagnosis_name


class DifferentialDiagnosisNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("approved or rejected differential diagnosis cannot be modified")


class ReviewRequiresPendingStatusError(DomainError):
    def __init__(self) -> None:
        super().__init__("only pending differential diagnosis can be marked as reviewed")
