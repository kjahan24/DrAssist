"""Data Transfer Objects for the Lab Results module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `LabResultSummaryDTO`
and `LabResultItemSummaryDTO` are also re-exported from `public/dto.py`
for other modules to depend on.

`CreateLabResultInput` deliberately has no `organization_id`/`patient_id`/
`visit_id`/`doctor_id` fields — see `domain/entities.py` for why those are
always derived from the linked `LabOrder`, never accepted as separate,
independently-trustable input.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.lab_results.domain.enums import AbnormalFlag, LabResultStatus

# --- CreateLabResult -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateLabResultInput:
    lab_order_id: UUID
    result_number: str
    reported_at: datetime
    laboratory_name: str | None = None
    comments: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateLabResultOutput:
    lab_result_id: UUID
    organization_id: UUID
    lab_order_id: UUID


# --- UpdateLabResult -------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateLabResultInput:
    lab_result_id: UUID
    laboratory_name: str | None = None
    comments: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateLabResultOutput:
    lab_result_id: UUID
    lab_order_id: UUID


# --- FinalizeLabResult ------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinalizeLabResultInput:
    lab_result_id: UUID


@dataclass(frozen=True, slots=True)
class FinalizeLabResultOutput:
    lab_result_id: UUID
    lab_order_id: UUID
    status: LabResultStatus


# --- AddLabResultItem -------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddLabResultItemInput:
    lab_result_id: UUID
    lab_order_item_id: UUID
    test_code: str
    test_name: str
    result_value: str
    abnormal_flag: AbnormalFlag
    result_unit: str | None = None
    reference_range: str | None = None
    interpretation: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddLabResultItemOutput:
    lab_result_item_id: UUID
    lab_result_id: UUID


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class LabResultItemSummaryDTO:
    lab_result_item_id: UUID
    lab_result_id: UUID
    lab_order_item_id: UUID
    test_code: str
    test_name: str
    result_value: str
    abnormal_flag: AbnormalFlag
    result_unit: str | None
    reference_range: str | None
    interpretation: str | None


@dataclass(frozen=True, slots=True)
class LabResultSummaryDTO:
    lab_result_id: UUID
    organization_id: UUID
    lab_order_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    result_number: str
    reported_at: datetime
    status: LabResultStatus
    laboratory_name: str | None
    comments: str | None
    items: list[LabResultItemSummaryDTO] = field(default_factory=list)
