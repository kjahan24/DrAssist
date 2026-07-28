"""Data Transfer Objects for the Doctor module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (`api/schemas.py`, not yet wired to any endpoint). Use-case
input/output DTOs are plain, immutable dataclasses; `DoctorSummaryDTO` is
also re-exported from `public/dto.py` for other modules to depend on.
"""

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from uuid import UUID

from app.modules.doctor.domain.enums import (
    DayOfWeek,
    DoctorStatus,
    Gender,
    LicenseVerificationStatus,
)

# --- OnboardDoctor ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OnboardDoctorInput:
    organization_id: UUID
    user_id: UUID
    employee_id: str
    joining_date: date
    full_name: str
    gender: Gender
    date_of_birth: date
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    biography: str | None = None
    years_of_experience: int = 0
    qualification: str | None = None
    consultation_fee: Decimal | None = None
    profile_photo_url: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class OnboardDoctorOutput:
    doctor_id: UUID
    organization_id: UUID
    user_id: UUID
    employee_id: str
    status: DoctorStatus
    profile_id: UUID


# --- AddDoctorLicense -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddDoctorLicenseInput:
    doctor_id: UUID
    license_number: str
    issuing_authority: str
    country: str
    issue_date: date
    expiry_date: date
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddDoctorLicenseOutput:
    license_id: UUID
    doctor_id: UUID
    license_number: str
    verification_status: LicenseVerificationStatus


# --- AddDoctorSpecialization ------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddDoctorSpecializationInput:
    doctor_id: UUID
    specialization_name: str
    is_primary: bool = False
    years_of_experience: int = 0
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddDoctorSpecializationOutput:
    specialization_id: UUID
    doctor_id: UUID
    specialization_name: str
    is_primary: bool


# --- AddDoctorSchedule -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddDoctorScheduleInput:
    doctor_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    is_available: bool = True
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class AddDoctorScheduleOutput:
    schedule_id: UUID
    doctor_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time


# --- Cross-cutting read models (also re-exported via public/dto.py) ----


@dataclass(frozen=True, slots=True)
class DoctorSummaryDTO:
    doctor_id: UUID
    organization_id: UUID
    user_id: UUID
    employee_id: str
    status: DoctorStatus
