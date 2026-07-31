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
    joining_date: date
    status: DoctorStatus

    @property
    def id(self) -> UUID:
        """Alias for `doctor_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.doctor_id


# --- Sub-resource read models (added by the REST APIs task) ----------------
# See `app.modules.patient.application.dto`'s own "Sub-resource read
# models" section for the full reasoning — identical situation here.


@dataclass(frozen=True, slots=True)
class DoctorProfileSummaryDTO:
    profile_id: UUID
    doctor_id: UUID
    full_name: str
    gender: Gender
    date_of_birth: date
    phone: str | None
    email: str | None
    address: str | None
    biography: str | None
    years_of_experience: int
    qualification: str | None
    consultation_fee: Decimal | None
    profile_photo_url: str | None

    @property
    def id(self) -> UUID:
        """Alias for `profile_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.profile_id


@dataclass(frozen=True, slots=True)
class DoctorLicenseSummaryDTO:
    license_id: UUID
    doctor_id: UUID
    license_number: str
    issuing_authority: str
    country: str
    issue_date: date
    expiry_date: date
    verification_status: LicenseVerificationStatus

    @property
    def id(self) -> UUID:
        """Alias for `license_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.license_id


@dataclass(frozen=True, slots=True)
class DoctorSpecializationSummaryDTO:
    specialization_id: UUID
    organization_id: UUID
    doctor_id: UUID
    specialization_name: str
    is_primary: bool
    years_of_experience: int

    @property
    def id(self) -> UUID:
        """Alias for `specialization_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.specialization_id


@dataclass(frozen=True, slots=True)
class DoctorScheduleEntrySummaryDTO:
    """Named `...EntrySummaryDTO`, not `DoctorScheduleSummaryDTO` — that
    name is already `app.modules.schedule.application.dto
    .DoctorScheduleSummaryDTO`'s, a materially different, separately
    persisted `DoctorSchedule` concept (adds `organization_id`/
    `slot_duration_minutes`) — see
    `app.modules.schedule.infrastructure.models`'s own docstring for the
    full discussion of this pre-existing naming collision between the two
    modules, which this task does not attempt to resolve."""

    schedule_id: UUID
    doctor_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    break_start: time | None
    break_end: time | None
    is_available: bool

    @property
    def id(self) -> UUID:
        """Alias for `schedule_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.schedule_id
