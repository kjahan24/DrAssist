"""Data Transfer Objects for the Lab Orders module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `LabOrderSummaryDTO`
and `LabOrderItemSummaryDTO` are also re-exported from `public/dto.py`
for other modules to depend on.

`CreateLabOrderInput` deliberately has no `organization_id`/`patient_id`/
`visit_id`/`doctor_id` fields — see `domain/entities.py` for why those are
always derived from the linked `ClinicalNote`, never accepted as
separate, independently-trustable input. `AddLabOrderItemInput`
deliberately has no `status` field either — an item always starts Draft
via the entity's own default; nothing in this task's business rules lets
a caller pick a different starting status.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority

# --- CreateLabOrder -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateLabOrderInput:
    clinical_note_id: UUID
    order_number: str
    ordered_at: datetime
    priority: Priority = Priority.ROUTINE
    clinical_information: str | None = None
    notes: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateLabOrderOutput:
    lab_order_id: UUID
    organization_id: UUID
    clinical_note_id: UUID


# --- UpdateLabOrder -------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateLabOrderInput:
    lab_order_id: UUID
    priority: Priority | None = None
    clinical_information: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateLabOrderOutput:
    lab_order_id: UUID
    clinical_note_id: UUID


# --- Status transitions ------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlaceLabOrderInput:
    lab_order_id: UUID


@dataclass(frozen=True, slots=True)
class MarkLabOrderCollectedInput:
    lab_order_id: UUID


@dataclass(frozen=True, slots=True)
class CancelLabOrderInput:
    lab_order_id: UUID


@dataclass(frozen=True, slots=True)
class LabOrderStatusOutput:
    lab_order_id: UUID
    clinical_note_id: UUID
    status: LabOrderStatus


# --- AddLabOrderItem -------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddLabOrderItemInput:
    lab_order_id: UUID
    test_code: str
    test_name: str
    specimen_type: str
    specimen_site: str | None = None
    instructions: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddLabOrderItemOutput:
    lab_order_item_id: UUID
    lab_order_id: UUID


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class LabOrderItemSummaryDTO:
    lab_order_item_id: UUID
    lab_order_id: UUID
    test_code: str
    test_name: str
    specimen_type: str
    status: LabOrderStatus
    specimen_site: str | None
    instructions: str | None

    @property
    def id(self) -> UUID:
        """Alias for `lab_order_item_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.lab_order_item_id


@dataclass(frozen=True, slots=True)
class LabOrderSummaryDTO:
    lab_order_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    order_number: str
    ordered_at: datetime
    priority: Priority
    status: LabOrderStatus
    clinical_information: str | None
    notes: str | None
    items: list[LabOrderItemSummaryDTO] = field(default_factory=list)

    @property
    def id(self) -> UUID:
        """Alias for `lab_order_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.lab_order_id
