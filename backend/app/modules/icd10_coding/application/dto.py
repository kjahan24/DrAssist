"""Data Transfer Objects for the ICD-10 Coding module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `ICD10CodingSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.

`CreateICD10CodingInput` deliberately has no `organization_id`/
`patient_id`/`visit_id`/`doctor_id` fields — see `domain/entities.py` for
why those are always derived from the linked `ClinicalNote`. It also has
no `review_status` field — that is derived from `coding_source`, never
independently supplied.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus

# --- CreateICD10Coding -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateICD10CodingInput:
    clinical_note_id: UUID
    icd10_code: str
    diagnosis_title: str
    coding_source: CodingSource
    differential_diagnosis_id: UUID | None = None
    primary_code: bool = False
    coding_notes: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateICD10CodingOutput:
    icd10_coding_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus


# --- UpdateICD10Coding -------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateICD10CodingInput:
    icd10_coding_id: UUID
    diagnosis_title: str | None = None
    coding_notes: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateICD10CodingOutput:
    icd10_coding_id: UUID
    clinical_note_id: UUID


# --- Primary transitions ------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkICD10CodingAsPrimaryInput:
    icd10_coding_id: UUID


@dataclass(frozen=True, slots=True)
class UnmarkICD10CodingAsPrimaryInput:
    icd10_coding_id: UUID


@dataclass(frozen=True, slots=True)
class ICD10CodingPrimaryOutput:
    icd10_coding_id: UUID
    clinical_note_id: UUID
    primary_code: bool


# --- Review workflow transitions ------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkICD10CodingReviewedInput:
    icd10_coding_id: UUID


@dataclass(frozen=True, slots=True)
class ApproveICD10CodingInput:
    icd10_coding_id: UUID


@dataclass(frozen=True, slots=True)
class RejectICD10CodingInput:
    icd10_coding_id: UUID


@dataclass(frozen=True, slots=True)
class ICD10CodingReviewStatusOutput:
    icd10_coding_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class ICD10CodingSummaryDTO:
    icd10_coding_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    icd10_code: str
    diagnosis_title: str
    coding_source: CodingSource
    primary_code: bool
    review_status: ReviewStatus
    differential_diagnosis_id: UUID | None
    coding_notes: str | None
