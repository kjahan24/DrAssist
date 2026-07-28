"""Pydantic v2 request/response schemas for the Patient module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `status`, ...) from the client —
see `docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from datetime import date
from uuid import UUID

from pydantic import EmailStr, Field

from app.modules.patient.domain.enums import (
    BloodGroup,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
)
from app.schemas.base import ORJSONModel


class PatientResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_number: str
    first_name: str
    middle_name: str | None = None
    last_name: str
    preferred_name: str | None = None
    gender: Gender
    date_of_birth: date
    blood_group: BloodGroup | None = None
    marital_status: MaritalStatus | None = None
    national_id: str | None = None
    passport_number: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
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
    status: PatientStatus


class RegisterPatientRequest(ORJSONModel):
    organization_id: UUID
    patient_number: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    gender: Gender
    date_of_birth: date
    blood_group: BloodGroup | None = None
    marital_status: MaritalStatus | None = None
    national_id: str | None = Field(default=None, max_length=64)
    passport_number: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    occupation: str | None = Field(default=None, max_length=100)
    nationality: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=50)
    religion: str | None = Field(default=None, max_length=100)
    address_line_1: str | None = Field(default=None, max_length=200)
    address_line_2: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=100)
    photo_url: str | None = Field(default=None, max_length=500)
    remarks: str | None = Field(default=None, max_length=1000)


class PatientContactResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    contact_type: ContactType
    phone_number: str
    email: EmailStr | None = None
    is_primary: bool
    is_verified: bool


class AddPatientContactRequest(ORJSONModel):
    contact_type: ContactType
    phone_number: str = Field(min_length=1, max_length=32)
    email: EmailStr | None = None
    is_primary: bool = False
    is_verified: bool = False


class EmergencyContactResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    full_name: str
    relationship: str
    phone_number: str
    email: EmailStr | None = None
    address: str | None = None
    priority: int | None = None
    is_primary: bool


class AddEmergencyContactRequest(ORJSONModel):
    full_name: str = Field(min_length=1, max_length=200)
    relationship: str = Field(min_length=1, max_length=100)
    phone_number: str = Field(min_length=1, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=500)
    priority: int | None = None
    is_primary: bool = False


class InsuranceResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    provider_name: str
    policy_number: str
    member_id: str | None = None
    group_number: str | None = None
    coverage_type: str | None = None
    effective_date: date
    expiry_date: date
    status: InsuranceStatus


class AddInsuranceRequest(ORJSONModel):
    provider_name: str = Field(min_length=1, max_length=200)
    policy_number: str = Field(min_length=1, max_length=100)
    member_id: str | None = Field(default=None, max_length=100)
    group_number: str | None = Field(default=None, max_length=100)
    coverage_type: str | None = Field(default=None, max_length=100)
    effective_date: date
    expiry_date: date
