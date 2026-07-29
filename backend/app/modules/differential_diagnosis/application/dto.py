"""Data Transfer Objects for the Differential Diagnosis module's
application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses;
`DifferentialDiagnosisSummaryDTO` is also re-exported from
`public/dto.py` for other modules to depend on.

`CreateDifferentialDiagnosisInput` deliberately has no `organization_id`/
`patient_id`/`visit_id`/`doctor_id` fields — see `domain/entities.py` for
why those are always derived from the linked `ClinicalNote`. It also has
no `review_status` field — that is derived from `diagnosis_source`,
never independently supplied.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus

# --- CreateDifferentialDiagnosis -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateDifferentialDiagnosisInput:
    clinical_note_id: UUID
    diagnosis_name: str
    diagnosis_source: DiagnosisSource
    ranking: int
    clinical_reasoning_id: UUID | None = None
    likelihood_score: float | None = None
    supporting_evidence: str | None = None
    excluded: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateDifferentialDiagnosisOutput:
    differential_diagnosis_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus


# --- UpdateDifferentialDiagnosis -------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateDifferentialDiagnosisInput:
    differential_diagnosis_id: UUID
    diagnosis_name: str | None = None
    likelihood_score: float | None = None
    supporting_evidence: str | None = None
    excluded: bool | None = None


@dataclass(frozen=True, slots=True)
class UpdateDifferentialDiagnosisOutput:
    differential_diagnosis_id: UUID
    clinical_note_id: UUID


# --- Review workflow transitions ------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkDifferentialDiagnosisReviewedInput:
    differential_diagnosis_id: UUID


@dataclass(frozen=True, slots=True)
class ApproveDifferentialDiagnosisInput:
    differential_diagnosis_id: UUID


@dataclass(frozen=True, slots=True)
class RejectDifferentialDiagnosisInput:
    differential_diagnosis_id: UUID


@dataclass(frozen=True, slots=True)
class DifferentialDiagnosisReviewStatusOutput:
    differential_diagnosis_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class DifferentialDiagnosisSummaryDTO:
    differential_diagnosis_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    diagnosis_name: str
    diagnosis_source: DiagnosisSource
    ranking: int
    review_status: ReviewStatus
    excluded: bool
    clinical_reasoning_id: UUID | None
    likelihood_score: float | None
    supporting_evidence: str | None
