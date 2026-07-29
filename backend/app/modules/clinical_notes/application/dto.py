"""Data Transfer Objects for the Clinical Notes module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `ClinicalNoteSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType

# --- CreateClinicalNote -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateClinicalNoteInput:
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    note_number: str
    note_type: ClinicalNoteType
    encounter_datetime: datetime
    chief_complaint_summary: str | None = None
    history_summary: str | None = None
    examination_summary: str | None = None
    assessment_summary: str | None = None
    plan_summary: str | None = None
    ai_generated: bool = False
    ai_model: str | None = None
    ai_version: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateClinicalNoteOutput:
    clinical_note_id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    note_number: str
    status: ClinicalNoteStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class ClinicalNoteSummaryDTO:
    clinical_note_id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    note_number: str
    note_type: ClinicalNoteType
    status: ClinicalNoteStatus
