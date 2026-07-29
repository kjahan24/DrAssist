"""Pydantic v2 request/response schemas for the Chief Complaints module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, ...) from the
client — see `docs/backend-architecture/07_security_layer.md §7`
(mass-assignment prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.chief_complaints.domain.enums import DurationUnit, Onset, Severity
from app.schemas.base import ORJSONModel


class VisitChiefComplaintResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    complaint: str
    duration_value: int | None = None
    duration_unit: DurationUnit | None = None
    severity: Severity | None = None
    onset: Onset | None = None
    notes: str | None = None
    recorded_by: UUID | None = None
    recorded_at: datetime


class RecordVisitChiefComplaintRequest(ORJSONModel):
    visit_id: UUID
    sequence_number: int = Field(ge=1)
    complaint: str = Field(min_length=1, max_length=500)
    recorded_at: datetime
    duration_value: int | None = Field(default=None, ge=0)
    duration_unit: DurationUnit | None = None
    severity: Severity | None = None
    onset: Onset | None = None
    notes: str | None = Field(default=None, max_length=1000)
    recorded_by: UUID | None = None
