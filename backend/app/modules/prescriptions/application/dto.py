"""Data Transfer Objects for the Prescription module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `PrescriptionSummaryDTO`
and `PrescriptionItemSummaryDTO` are also re-exported from `public/dto.py`
for other modules to depend on.

`CreatePrescriptionInput` deliberately has no `organization_id`/
`patient_id`/`visit_id`/`doctor_id` fields — see `domain/entities.py` for
why those are always derived from the linked `ClinicalNote`, never
accepted as separate, independently-trustable input.
`AddPrescriptionItemInput` deliberately has no `prescription_id`-adjacent
identity fields beyond `prescription_id` itself, for the same reason.
"""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from app.modules.prescriptions.domain.enums import AdministrationRoute, PrescriptionStatus

# --- CreatePrescription -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreatePrescriptionInput:
    clinical_note_id: UUID
    prescription_number: str
    prescription_date: date
    notes: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreatePrescriptionOutput:
    prescription_id: UUID
    organization_id: UUID
    clinical_note_id: UUID


# --- UpdatePrescription -------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdatePrescriptionInput:
    prescription_id: UUID
    prescription_date: date | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class UpdatePrescriptionOutput:
    prescription_id: UUID
    clinical_note_id: UUID


# --- FinalizePrescription ------------------------------------------------


@dataclass(frozen=True, slots=True)
class FinalizePrescriptionInput:
    prescription_id: UUID


@dataclass(frozen=True, slots=True)
class FinalizePrescriptionOutput:
    prescription_id: UUID
    clinical_note_id: UUID
    status: PrescriptionStatus


# --- AddPrescriptionItem -------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPrescriptionItemInput:
    prescription_id: UUID
    medication_name: str
    strength: str
    dosage: str
    dosage_unit: str
    frequency: str
    route: AdministrationRoute
    duration: str
    duration_unit: str
    quantity: str
    generic_name: str | None = None
    instructions: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddPrescriptionItemOutput:
    prescription_item_id: UUID
    prescription_id: UUID


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class PrescriptionItemSummaryDTO:
    prescription_item_id: UUID
    prescription_id: UUID
    medication_name: str
    strength: str
    dosage: str
    dosage_unit: str
    frequency: str
    route: AdministrationRoute
    duration: str
    duration_unit: str
    quantity: str
    generic_name: str | None
    instructions: str | None


@dataclass(frozen=True, slots=True)
class PrescriptionSummaryDTO:
    prescription_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    prescription_number: str
    prescription_date: date
    status: PrescriptionStatus
    notes: str | None
    items: list[PrescriptionItemSummaryDTO] = field(default_factory=list)
