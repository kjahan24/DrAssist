"""Pydantic v2 request/response schemas for the Prescription module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, `patient_id`,
`visit_id`, `doctor_id`, `status`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `patient_id`/`visit_id`/`doctor_id`/`organization_id` in
particular are never client-settable at all: they are always derived
from the linked `ClinicalNote` — see `domain/entities.py`.
"""

from datetime import date
from uuid import UUID

from pydantic import Field

from app.modules.prescriptions.domain.enums import AdministrationRoute, PrescriptionStatus
from app.schemas.base import ORJSONModel


class PrescriptionItemResponse(ORJSONModel):
    id: UUID
    prescription_id: UUID
    medication_name: str
    generic_name: str | None = None
    strength: str
    dosage: str
    dosage_unit: str
    frequency: str
    route: AdministrationRoute
    duration: str
    duration_unit: str
    quantity: str
    instructions: str | None = None


class PrescriptionResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    prescription_number: str
    prescription_date: date
    status: PrescriptionStatus
    notes: str | None = None
    items: list[PrescriptionItemResponse] = Field(default_factory=list)


class CreatePrescriptionRequest(ORJSONModel):
    clinical_note_id: UUID
    prescription_number: str = Field(max_length=64)
    prescription_date: date
    notes: str | None = Field(default=None, max_length=2000)


class UpdatePrescriptionRequest(ORJSONModel):
    prescription_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AddPrescriptionItemRequest(ORJSONModel):
    medication_name: str = Field(max_length=255)
    generic_name: str | None = Field(default=None, max_length=255)
    strength: str = Field(max_length=100)
    dosage: str = Field(max_length=100)
    dosage_unit: str = Field(max_length=50)
    frequency: str = Field(max_length=100)
    route: AdministrationRoute
    duration: str = Field(max_length=50)
    duration_unit: str = Field(max_length=50)
    quantity: str = Field(max_length=50)
    instructions: str | None = Field(default=None, max_length=1000)
