"""Pydantic v2 request/response schemas for the Doctor module.

Wired to `api/router.py`'s live endpoints. Schemas never expose a domain
entity directly, and never accept server-controlled fields (`id`,
`status`, `verification_status`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).

`DoctorScheduleResponse`/`AddDoctorScheduleRequest` back the module's
deprecated schedule endpoints — see
`app.modules.doctor.domain.entities.DoctorSchedule`'s own docstring and
`docs/backend-architecture/14_doctor_schedule_ownership.md`.
"""

from datetime import date, time
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field

from app.modules.doctor.domain.enums import (
    DayOfWeek,
    DoctorStatus,
    Gender,
    LicenseVerificationStatus,
)
from app.schemas.base import ORJSONModel


class DoctorResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    employee_id: str
    status: DoctorStatus
    joining_date: date


class DoctorProfileResponse(ORJSONModel):
    id: UUID
    doctor_id: UUID
    full_name: str
    gender: Gender
    date_of_birth: date
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    biography: str | None = None
    years_of_experience: int
    qualification: str | None = None
    consultation_fee: Decimal | None = None
    profile_photo_url: str | None = None


class DoctorLicenseResponse(ORJSONModel):
    id: UUID
    doctor_id: UUID
    license_number: str
    issuing_authority: str
    country: str
    issue_date: date
    expiry_date: date
    verification_status: LicenseVerificationStatus


class DoctorSpecializationResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    doctor_id: UUID
    specialization_name: str
    is_primary: bool
    years_of_experience: int


class DoctorScheduleResponse(ORJSONModel):
    id: UUID
    doctor_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    is_available: bool


class OnboardDoctorRequest(ORJSONModel):
    """No `organization_id` field — see
    `app.modules.patient.api.schemas.RegisterPatientRequest`'s own
    docstring for why (identical fix, applied by the same task)."""

    user_id: UUID
    employee_id: str = Field(min_length=1, max_length=64)
    joining_date: date
    full_name: str = Field(min_length=1, max_length=200)
    gender: Gender
    date_of_birth: date
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=500)
    biography: str | None = Field(default=None, max_length=2000)
    years_of_experience: int = Field(default=0, ge=0)
    qualification: str | None = Field(default=None, max_length=200)
    consultation_fee: Decimal | None = Field(default=None, ge=0)
    profile_photo_url: str | None = Field(default=None, max_length=500)


class AddDoctorLicenseRequest(ORJSONModel):
    license_number: str = Field(min_length=1, max_length=100)
    issuing_authority: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=1, max_length=100)
    issue_date: date
    expiry_date: date


class AddDoctorSpecializationRequest(ORJSONModel):
    specialization_name: str = Field(min_length=1, max_length=200)
    is_primary: bool = False
    years_of_experience: int = Field(default=0, ge=0)


class AddDoctorScheduleRequest(ORJSONModel):
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    is_available: bool = True
