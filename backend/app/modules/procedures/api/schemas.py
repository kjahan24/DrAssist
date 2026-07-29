"""Pydantic v2 request/response schemas for the Procedures module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, ...) from the
client — see `docs/backend-architecture/07_security_layer.md §7`
(mass-assignment prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.procedures.domain.enums import ProcedureStatus
from app.schemas.base import ORJSONModel


class VisitProcedureResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    procedure_name: str
    procedure_code: str | None = None
    procedure_category: str | None = None
    procedure_status: ProcedureStatus
    performed_by: UUID | None = None
    performed_at: datetime | None = None
    notes: str | None = None


class RecordVisitProcedureRequest(ORJSONModel):
    visit_id: UUID
    sequence_number: int = Field(ge=1)
    procedure_name: str = Field(min_length=1, max_length=500)
    procedure_code: str | None = Field(default=None, max_length=50)
    procedure_category: str | None = Field(default=None, max_length=100)
    procedure_status: ProcedureStatus = ProcedureStatus.PLANNED
    performed_by: UUID | None = None
    performed_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)
