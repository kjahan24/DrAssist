"""Pydantic v2 request/response schemas for the Vital Signs module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `bmi`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `bmi` in particular is never client-settable — it is always
derived from `height_cm`/`weight_kg`.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ORJSONModel


class VisitVitalSignsResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    visit_id: UUID
    recorded_by: UUID | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    bmi: Decimal | None = None
    temperature_c: Decimal
    pulse_bpm: int
    respiratory_rate: int
    systolic_bp: int
    diastolic_bp: int
    spo2: int
    blood_glucose: Decimal | None = None
    pain_score: int | None = None
    recorded_at: datetime


class RecordVisitVitalSignsRequest(ORJSONModel):
    visit_id: UUID
    recorded_by: UUID | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    temperature_c: Decimal = Field(ge=Decimal("25.0"), le=Decimal("45.0"))
    pulse_bpm: int = Field(gt=0)
    respiratory_rate: int = Field(gt=0)
    systolic_bp: int
    diastolic_bp: int
    spo2: int = Field(ge=0, le=100)
    blood_glucose: Decimal | None = None
    pain_score: int | None = Field(default=None, ge=0, le=10)
    recorded_at: datetime
