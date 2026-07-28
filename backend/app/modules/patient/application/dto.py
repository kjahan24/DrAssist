"""Data Transfer Objects for the Patient module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `PatientSummaryDTO` is
also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient.domain.enums import (
    BloodGroup,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
)

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


# --- AddPatientContact ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPatientContactInput:
    patient_id: UUID
    contact_type: ContactType
    phone_number: str
    email: str | None = None
    is_primary: bool = False
    is_verified: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddPatientContactOutput:
    contact_id: UUID
    patient_id: UUID
    contact_type: ContactType
    is_primary: bool


# --- AddEmergencyContact -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddEmergencyContactInput:
    patient_id: UUID
    full_name: str
    relationship: str
    phone_number: str
    email: str | None = None
    address: str | None = None
    priority: int | None = None
    is_primary: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddEmergencyContactOutput:
    contact_id: UUID
    patient_id: UUID
    full_name: str
    is_primary: bool


# --- AddInsurance -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddInsuranceInput:
    patient_id: UUID
    provider_name: str
    policy_number: str
    effective_date: date
    expiry_date: date
    member_id: str | None = None
    group_number: str | None = None
    coverage_type: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddInsuranceOutput:
    insurance_id: UUID
    patient_id: UUID
    policy_number: str
    status: InsuranceStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class PatientSummaryDTO:
    patient_id: UUID
    organization_id: UUID
    patient_number: str
    first_name: str
    last_name: str
    status: PatientStatus
