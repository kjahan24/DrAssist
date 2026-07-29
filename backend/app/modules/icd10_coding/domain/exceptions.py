"""Domain exceptions for the ICD-10 Coding module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ClinicalNoteNotFoundError` and `DifferentialDiagnosisNotFoundError` are
defined locally rather than reused from
`app.modules.clinical_notes.domain.exceptions`/
`app.modules.differential_diagnosis.domain.exceptions` — the same
situation every prior child-document module documents: neither owning
module exposes a "not found" error a peer module is allowed to import, so
every module that *references* an existing row by id defines the
exception locally.

Unlike `app.modules.soap_notes.application.use_cases.create_soap_note
.CreateSOAPNote`/`app.modules.prescriptions.application.use_cases
.create_prescription.CreatePrescription` (both of which reuse
`ClinicalNoteNotEditableError` because their own business rules
explicitly tie read-only enforcement to the *parent*'s status), this
module's use cases never check `ClinicalNoteQueryPort.is_editable` or
`DifferentialDiagnosisQueryPort.is_editable` — this task's Business Rules
never say "if the linked Clinical Note/Differential Diagnosis is X, this
becomes read-only". The only immutability rule stated is entirely about
this aggregate's *own* `review_status` ("Approved and Rejected codes
become read-only") — the same "only encode business rules explicitly
stated for the module being built" reasoning
`app.modules.differential_diagnosis.domain.exceptions` already
establishes. See `domain/entities.py` for the full reasoning.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class ClinicalNoteNotFoundError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"no clinical note found with id {clinical_note_id}")
        self.clinical_note_id = clinical_note_id


class DifferentialDiagnosisNotFoundError(DomainError):
    def __init__(self, differential_diagnosis_id: UUID) -> None:
        super().__init__(f"no differential diagnosis found with id {differential_diagnosis_id}")
        self.differential_diagnosis_id = differential_diagnosis_id


class DifferentialDiagnosisClinicalNoteMismatchError(DomainError):
    def __init__(self, differential_diagnosis_id: UUID, clinical_note_id: UUID) -> None:
        super().__init__(
            f"differential diagnosis {differential_diagnosis_id} does not belong to clinical "
            f"note {clinical_note_id}"
        )
        self.differential_diagnosis_id = differential_diagnosis_id
        self.clinical_note_id = clinical_note_id


class ICD10CodingNotFoundError(DomainError):
    def __init__(self, icd10_coding_id: UUID) -> None:
        super().__init__(f"no ICD-10 coding record found with id {icd10_coding_id}")
        self.icd10_coding_id = icd10_coding_id


class ICD10CodeRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("icd10_code must not be blank")


class DiagnosisTitleRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("diagnosis_title must not be blank")


class DuplicateICD10CodeError(DomainError):
    def __init__(self, clinical_note_id: UUID, icd10_code: str) -> None:
        super().__init__(
            f"icd10_code {icd10_code!r} already exists for clinical note {clinical_note_id}"
        )
        self.clinical_note_id = clinical_note_id
        self.icd10_code = icd10_code


class DuplicatePrimaryCodeError(DomainError):
    def __init__(self, clinical_note_id: UUID) -> None:
        super().__init__(f"clinical note {clinical_note_id} already has a primary ICD-10 code")
        self.clinical_note_id = clinical_note_id


class ICD10CodingNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("approved or rejected ICD-10 coding cannot be modified")


class ReviewRequiresPendingStatusError(DomainError):
    def __init__(self) -> None:
        super().__init__("only pending ICD-10 coding can be marked as reviewed")
