"""Pydantic v2 request/response schemas for the Lab Orders module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, `patient_id`,
`visit_id`, `doctor_id`, `status`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `patient_id`/`visit_id`/`doctor_id`/`organization_id` in
particular are never client-settable at all: they are always derived
from the linked `ClinicalNote` — see `domain/entities.py`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.schemas.base import ORJSONModel


class LabOrderItemResponse(ORJSONModel):
    id: UUID
    lab_order_id: UUID
    test_code: str
    test_name: str
    specimen_type: str
    specimen_site: str | None = None
    status: LabOrderStatus
    instructions: str | None = None


class LabOrderResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    order_number: str
    ordered_at: datetime
    priority: Priority
    status: LabOrderStatus
    clinical_information: str | None = None
    notes: str | None = None
    items: list[LabOrderItemResponse] = Field(default_factory=list)


class CreateLabOrderRequest(ORJSONModel):
    clinical_note_id: UUID
    order_number: str = Field(max_length=64)
    ordered_at: datetime
    priority: Priority = Priority.ROUTINE
    clinical_information: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class UpdateLabOrderRequest(ORJSONModel):
    priority: Priority | None = None
    clinical_information: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class AddLabOrderItemRequest(ORJSONModel):
    test_code: str = Field(max_length=64)
    test_name: str = Field(max_length=255)
    specimen_type: str = Field(max_length=100)
    specimen_site: str | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=1000)
