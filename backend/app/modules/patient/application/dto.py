"""Data Transfer Objects for the Patient module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `PatientSummaryDTO` is
also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient.domain.enums import BloodGroup, Gender, MaritalStatus, PatientStatus

# --- RegisterPatient --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegisterPatientInput:
    organization_id: UUID
    patient_number: str
    first_name: str
    last_name: str
    gender: Gender
    date_of_birth: date
    middle_name: str | None = None
    preferred_name: str | None = None
    blood_group: BloodGroup | None = None
    marital_status: MaritalStatus | None = None
    national_id: str | None = None
    passport_number: str | None = None
    phone: str | None = None
    email: str | None = None
    occupation: str | None = None
    nationality: str | None = None
    language: str | None = None
    religion: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    photo_url: str | None = None
    remarks: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RegisterPatientOutput:
    patient_id: UUID
    organization_id: UUID
    patient_number: str
    status: PatientStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class PatientSummaryDTO:
    patient_id: UUID
    organization_id: UUID
    patient_number: str
    first_name: str
    last_name: str
    status: PatientStatus
