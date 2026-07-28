"""Data Transfer Objects for the Vital Signs module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `VitalSignsSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

# --- RecordVisitVitalSigns ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordVisitVitalSignsInput:
    visit_id: UUID
    temperature_c: Decimal
    pulse_bpm: int
    respiratory_rate: int
    systolic_bp: int
    diastolic_bp: int
    spo2: int
    recorded_at: datetime
    recorded_by: UUID | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    blood_glucose: Decimal | None = None
    pain_score: int | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordVisitVitalSignsOutput:
    vital_signs_id: UUID
    organization_id: UUID
    visit_id: UUID
    bmi: Decimal | None


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class VitalSignsSummaryDTO:
    vital_signs_id: UUID
    organization_id: UUID
    visit_id: UUID
    recorded_at: datetime
    bmi: Decimal | None
