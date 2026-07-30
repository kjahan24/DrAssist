"""Data Transfer Objects for the Patient History module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (this task builds no HTTP endpoint — see `api/router.py`).
Use-case input/output DTOs are plain, immutable dataclasses;
`PatientHistorySummaryDTO` is also re-exported from `public/dto.py` for
other modules to depend on.

`CreatePatientHistoryInput` deliberately has no `organization_id`/
`patient_id`/`visit_id` fields — see `domain/entities.py` for why those
are always derived from the linked, *approved* Doctor Review. There is
no `Update...`/`...Output` pair beyond creation: "History records are
immutable" — this module has exactly one write operation.

`encounter_date` is caller-supplied rather than derived from the linked
Clinical Note: `app.modules.clinical_notes.public.dto
.ClinicalNoteSummaryDTO` does not expose the note's `encounter_datetime`
today, and extending that DTO is not "absolutely necessary" (rule 1)
when the caller already has the originating artifact's own timestamp in
hand at the point it decides to record history for it.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient_history.domain.enums import HistoryType, ReferenceType

# --- CreatePatientHistory -------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreatePatientHistoryInput:
    doctor_review_id: UUID
    history_type: HistoryType
    reference_type: ReferenceType
    reference_id: UUID
    encounter_date: date
    summary: str
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreatePatientHistoryOutput:
    patient_history_id: UUID
    organization_id: UUID
    patient_id: UUID
    history_type: HistoryType
    reference_type: ReferenceType


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class PatientHistorySummaryDTO:
    patient_history_id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_review_id: UUID
    history_type: HistoryType
    reference_type: ReferenceType
    reference_id: UUID
    encounter_date: date
    summary: str
    created_from_review: bool
