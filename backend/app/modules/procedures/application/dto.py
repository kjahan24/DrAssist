"""Data Transfer Objects for the Procedures module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `ProcedureSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.procedures.domain.enums import ProcedureStatus

# --- RecordVisitProcedure -----------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordVisitProcedureInput:
    visit_id: UUID
    sequence_number: int
    procedure_name: str
    procedure_code: str | None = None
    procedure_category: str | None = None
    procedure_status: ProcedureStatus = ProcedureStatus.PLANNED
    performed_by: UUID | None = None
    performed_at: datetime | None = None
    notes: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordVisitProcedureOutput:
    procedure_id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    procedure_status: ProcedureStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class ProcedureSummaryDTO:
    procedure_id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    procedure_name: str
    procedure_status: ProcedureStatus
