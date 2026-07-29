"""Data Transfer Objects for the Chief Complaints module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `ChiefComplaintSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.chief_complaints.domain.enums import DurationUnit, Onset, Severity

# --- RecordVisitChiefComplaint -----------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordVisitChiefComplaintInput:
    visit_id: UUID
    sequence_number: int
    complaint: str
    recorded_at: datetime
    duration_value: int | None = None
    duration_unit: DurationUnit | None = None
    severity: Severity | None = None
    onset: Onset | None = None
    notes: str | None = None
    recorded_by: UUID | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordVisitChiefComplaintOutput:
    chief_complaint_id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class ChiefComplaintSummaryDTO:
    chief_complaint_id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    complaint: str
