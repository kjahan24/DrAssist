"""Pydantic v2 request/response schemas for the Lab Results module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, `patient_id`,
`visit_id`, `doctor_id`, `status`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `patient_id`/`visit_id`/`doctor_id`/`organization_id` in
particular are never client-settable at all: they are always derived
from the linked `LabOrder` — see `domain/entities.py`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.lab_results.domain.enums import AbnormalFlag, LabResultStatus
from app.schemas.base import ORJSONModel


class LabResultItemResponse(ORJSONModel):
    id: UUID
    lab_result_id: UUID
    lab_order_item_id: UUID
    test_code: str
    test_name: str
    result_value: str
    result_unit: str | None = None
    reference_range: str | None = None
    abnormal_flag: AbnormalFlag
    interpretation: str | None = None


class LabResultResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    lab_order_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    result_number: str
    reported_at: datetime
    status: LabResultStatus
    laboratory_name: str | None = None
    comments: str | None = None
    items: list[LabResultItemResponse] = Field(default_factory=list)


class CreateLabResultRequest(ORJSONModel):
    lab_order_id: UUID
    result_number: str = Field(max_length=64)
    reported_at: datetime
    laboratory_name: str | None = Field(default=None, max_length=255)
    comments: str | None = Field(default=None, max_length=2000)


class UpdateLabResultRequest(ORJSONModel):
    laboratory_name: str | None = Field(default=None, max_length=255)
    comments: str | None = Field(default=None, max_length=2000)


class AddLabResultItemRequest(ORJSONModel):
    lab_order_item_id: UUID
    test_code: str = Field(max_length=64)
    test_name: str = Field(max_length=255)
    result_value: str = Field(max_length=255)
    result_unit: str | None = Field(default=None, max_length=50)
    reference_range: str | None = Field(default=None, max_length=100)
    abnormal_flag: AbnormalFlag
    interpretation: str | None = Field(default=None, max_length=1000)
