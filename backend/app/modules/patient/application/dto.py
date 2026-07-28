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
    AdherenceStatus,
    AllergySeverity,
    AllergyStatus,
    AllergyType,
    BloodGroup,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
    RouteOfAdministration,
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


# --- RecordPatientAllergy ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordPatientAllergyInput:
    patient_id: UUID
    allergy_type: AllergyType
    allergen_name: str
    severity: AllergySeverity
    reaction: str | None = None
    onset_date: date | None = None
    notes: str | None = None
    verified_by: UUID | None = None
    verified_date: date | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordPatientAllergyOutput:
    allergy_id: UUID
    patient_id: UUID
    allergen_name: str
    severity: AllergySeverity
    status: AllergyStatus


# --- AddPatientMedication -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddPatientMedicationInput:
    patient_id: UUID
    medication_name: str
    dosage: str
    route: RouteOfAdministration
    start_date: date
    prescribed_by: UUID | None = None
    generic_name: str | None = None
    brand_name: str | None = None
    dosage_unit: str | None = None
    frequency: str | None = None
    indication: str | None = None
    end_date: date | None = None
    is_current: bool = True
    adherence_status: AdherenceStatus = AdherenceStatus.TAKING
    instructions: str | None = None
    notes: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddPatientMedicationOutput:
    medication_id: UUID
    patient_id: UUID
    medication_name: str
    is_current: bool
    adherence_status: AdherenceStatus


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class PatientSummaryDTO:
    patient_id: UUID
    organization_id: UUID
    patient_number: str
    first_name: str
    last_name: str
    status: PatientStatus
