"""Data Transfer Objects for the SOAP Notes module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `SOAPNoteSummaryDTO`
is also re-exported from `public/dto.py` for other modules to depend on.

`CreateSOAPNoteInput` deliberately has no `organization_id`/`patient_id`/
`visit_id`/`doctor_id` fields — see `domain/entities.py` for why those
are always derived from the linked `ClinicalNote`, never accepted as
separate, independently-trustable input.
"""

from dataclasses import dataclass
from uuid import UUID

# --- CreateSOAPNote -----------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateSOAPNoteInput:
    clinical_note_id: UUID
    chief_complaint: str | None = None
    history_of_present_illness: str | None = None
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vital_sign_summary: str | None = None
    assessment: str | None = None
    plan: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateSOAPNoteOutput:
    soap_note_id: UUID
    organization_id: UUID
    clinical_note_id: UUID


# --- UpdateSOAPNote -----------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateSOAPNoteInput:
    soap_note_id: UUID
    chief_complaint: str | None = None
    history_of_present_illness: str | None = None
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vital_sign_summary: str | None = None
    assessment: str | None = None
    plan: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateSOAPNoteOutput:
    soap_note_id: UUID
    clinical_note_id: UUID


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class SOAPNoteSummaryDTO:
    soap_note_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    chief_complaint: str | None
    history_of_present_illness: str | None
    review_of_systems: str | None
    physical_examination: str | None
    vital_sign_summary: str | None
    assessment: str | None
    plan: str | None
