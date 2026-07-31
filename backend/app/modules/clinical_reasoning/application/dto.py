"""Data Transfer Objects for the Clinical Reasoning module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses;
`ClinicalReasoningSummaryDTO` is also re-exported from `public/dto.py`
for other modules to depend on.

`CreateClinicalReasoningInput` deliberately has no `organization_id`/
`patient_id`/`visit_id`/`doctor_id` fields — see `domain/entities.py` for
why those are always derived from the linked `ClinicalNote`. It also has
no `review_status`/`reviewed_by_doctor` fields — both are derived from
`ai_generated` at creation, never independently supplied.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus

# --- CreateClinicalReasoning -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateClinicalReasoningInput:
    clinical_note_id: UUID
    reasoning_source: ReasoningSource
    reasoning_text: str
    ai_generated: bool
    confidence_score: float | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateClinicalReasoningOutput:
    clinical_reasoning_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus


# --- UpdateClinicalReasoning -------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateClinicalReasoningInput:
    clinical_reasoning_id: UUID
    reasoning_text: str | None = None
    confidence_score: float | None = None


@dataclass(frozen=True, slots=True)
class UpdateClinicalReasoningOutput:
    clinical_reasoning_id: UUID
    clinical_note_id: UUID


# --- Review workflow transitions ------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkClinicalReasoningReviewedInput:
    clinical_reasoning_id: UUID


@dataclass(frozen=True, slots=True)
class ApproveClinicalReasoningInput:
    clinical_reasoning_id: UUID


@dataclass(frozen=True, slots=True)
class RejectClinicalReasoningInput:
    clinical_reasoning_id: UUID


@dataclass(frozen=True, slots=True)
class ClinicalReasoningReviewStatusOutput:
    clinical_reasoning_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class ClinicalReasoningSummaryDTO:
    clinical_reasoning_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    reasoning_source: ReasoningSource
    reasoning_text: str
    ai_generated: bool
    review_status: ReviewStatus
    reviewed_by_doctor: bool
    confidence_score: float | None

    @property
    def id(self) -> UUID:
        """Alias for `clinical_reasoning_id` — see
        `AppointmentSummaryDTO.id`'s own docstring in
        `app.modules.appointment.application.dto` for the full reasoning
        (identical situation in every module)."""
        return self.clinical_reasoning_id
