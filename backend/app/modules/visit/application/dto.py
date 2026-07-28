"""Data Transfer Objects for the Visit module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `VisitSummaryDTO` is
also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.visit.domain.enums import VisitPriority, VisitStatus, VisitType

# --- ScheduleVisit -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ScheduleVisitInput:
    patient_id: UUID
    doctor_id: UUID
    visit_number: str
    visit_type: VisitType
    visit_date: date
    appointment_id: UUID | None = None
    priority: VisitPriority = VisitPriority.NORMAL
    chief_complaint_summary: str | None = None
    reason_for_visit: str | None = None
    room_number: str | None = None
    follow_up_required: bool = False
    follow_up_date: date | None = None
    notes: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ScheduleVisitOutput:
    visit_id: UUID
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    visit_number: str
    visit_status: VisitStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class VisitSummaryDTO:
    visit_id: UUID
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    visit_number: str
    visit_status: VisitStatus
