"""Doctor module aggregate roots: Doctor, DoctorProfile, DoctorLicense,
DoctorSpecialization, DoctorSchedule.

Each aggregate reference to another aggregate is by ID only (never an
object reference) — see the aggregate-reference rule in
`docs/backend-architecture/03_module_architecture.md`. `DoctorProfile` is
its own aggregate (one-to-one with `Doctor`) for the same reason
`OrganizationSettings` is independent of `Organization`: it's edited
independently and doesn't need to be loaded/locked together with `Doctor`
for any invariant this module enforces. `DoctorLicense`,
`DoctorSpecialization`, and `DoctorSchedule` are one-to-many with `Doctor`
and are likewise their own aggregates, matching the explicit five-entity
scope of this module. All mutation goes through named methods that
enforce the aggregate's invariants and record domain events; nothing here
performs I/O.
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
from app.modules.doctor.domain.events import (
    DoctorActivated,
    DoctorDeactivated,
    DoctorLicenseAdded,
    DoctorLicenseRejected,
    DoctorLicenseVerified,
    DoctorOnboarded,
    DoctorProfileCreated,
    DoctorProfileUpdated,
    DoctorScheduleAdded,
    DoctorSpecializationAdded,
    DoctorSuspended,
)
from app.modules.doctor.domain.exceptions import (
    DoctorProfileNameRequiredError,
    EmployeeIdRequiredError,
    InvalidBreakTimeError,
    InvalidConsultationFeeError,
    InvalidLicenseDateRangeError,
    InvalidScheduleTimeRangeError,
    InvalidYearsOfExperienceError,
    LicenseNumberRequiredError,
    SpecializationNameRequiredError,
)
from app.shared.domain.common_value_objects import EmailAddress
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Doctor(AggregateRoot):
    organization_id: UUID
    user_id: UUID
    employee_id: str
    joining_date: date
    status: DoctorStatus = DoctorStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.employee_id or not self.employee_id.strip():
            raise EmployeeIdRequiredError()
        self.employee_id = self.employee_id.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        user_id: UUID,
        employee_id: str,
        joining_date: date,
    ) -> "Doctor":
        doctor = cls(
            organization_id=organization_id,
            user_id=user_id,
            employee_id=employee_id,
            joining_date=joining_date,
        )
        doctor.record_event(
            DoctorOnboarded(
                doctor_id=doctor.id,
                organization_id=organization_id,
                user_id=user_id,
                employee_id=doctor.employee_id,
            )
        )
        return doctor

    def activate(self) -> None:
        if self.status is DoctorStatus.ACTIVE:
            return
        self.status = DoctorStatus.ACTIVE
        self.touch()
        self.record_event(DoctorActivated(doctor_id=self.id))

    def deactivate(self) -> None:
        if self.status is DoctorStatus.INACTIVE:
            return
        self.status = DoctorStatus.INACTIVE
        self.touch()
        self.record_event(DoctorDeactivated(doctor_id=self.id))

    def suspend(self) -> None:
        if self.status is DoctorStatus.SUSPENDED:
            return
        self.status = DoctorStatus.SUSPENDED
        self.touch()
        self.record_event(DoctorSuspended(doctor_id=self.id))


@dataclass(kw_only=True, eq=False)
class DoctorProfile(AggregateRoot):
    doctor_id: UUID
    full_name: str
    gender: Gender
    date_of_birth: date
    phone: str | None = None
    email: EmailAddress | None = None
    address: str | None = None
    biography: str | None = None
    years_of_experience: int = 0
    qualification: str | None = None
    consultation_fee: Decimal | None = None
    profile_photo_url: str | None = None

    def __post_init__(self) -> None:
        if not self.full_name or not self.full_name.strip():
            raise DoctorProfileNameRequiredError()
        self.full_name = self.full_name.strip()
        _validate_years_of_experience(self.years_of_experience)
        _validate_consultation_fee(self.consultation_fee)

    @classmethod
    def create(
        cls,
        *,
        doctor_id: UUID,
        full_name: str,
        gender: Gender,
        date_of_birth: date,
        phone: str | None = None,
        email: EmailAddress | None = None,
        address: str | None = None,
        biography: str | None = None,
        years_of_experience: int = 0,
        qualification: str | None = None,
        consultation_fee: Decimal | None = None,
        profile_photo_url: str | None = None,
    ) -> "DoctorProfile":
        profile = cls(
            doctor_id=doctor_id,
            full_name=full_name,
            gender=gender,
            date_of_birth=date_of_birth,
            phone=phone,
            email=email,
            address=address,
            biography=biography,
            years_of_experience=years_of_experience,
            qualification=qualification,
            consultation_fee=consultation_fee,
            profile_photo_url=profile_photo_url,
        )
        profile.record_event(DoctorProfileCreated(doctor_id=doctor_id, profile_id=profile.id))
        return profile

    def update(
        self,
        *,
        full_name: str | None = None,
        gender: Gender | None = None,
        date_of_birth: date | None = None,
        phone: str | None = None,
        email: EmailAddress | None = None,
        address: str | None = None,
        biography: str | None = None,
        years_of_experience: int | None = None,
        qualification: str | None = None,
        consultation_fee: Decimal | None = None,
        profile_photo_url: str | None = None,
    ) -> None:
        if full_name is not None:
            if not full_name.strip():
                raise DoctorProfileNameRequiredError()
            self.full_name = full_name.strip()
        if gender is not None:
            self.gender = gender
        if date_of_birth is not None:
            self.date_of_birth = date_of_birth
        if phone is not None:
            self.phone = phone
        if email is not None:
            self.email = email
        if address is not None:
            self.address = address
        if biography is not None:
            self.biography = biography
        if years_of_experience is not None:
            _validate_years_of_experience(years_of_experience)
            self.years_of_experience = years_of_experience
        if qualification is not None:
            self.qualification = qualification
        if consultation_fee is not None:
            _validate_consultation_fee(consultation_fee)
            self.consultation_fee = consultation_fee
        if profile_photo_url is not None:
            self.profile_photo_url = profile_photo_url

        self.touch()
        self.record_event(DoctorProfileUpdated(doctor_id=self.doctor_id, profile_id=self.id))


@dataclass(kw_only=True, eq=False)
class DoctorLicense(AggregateRoot):
    doctor_id: UUID
    license_number: str
    issuing_authority: str
    country: str
    issue_date: date
    expiry_date: date
    verification_status: LicenseVerificationStatus = LicenseVerificationStatus.PENDING

    def __post_init__(self) -> None:
        if not self.license_number or not self.license_number.strip():
            raise LicenseNumberRequiredError()
        self.license_number = self.license_number.strip()
        if self.expiry_date <= self.issue_date:
            raise InvalidLicenseDateRangeError()

    @classmethod
    def create(
        cls,
        *,
        doctor_id: UUID,
        license_number: str,
        issuing_authority: str,
        country: str,
        issue_date: date,
        expiry_date: date,
    ) -> "DoctorLicense":
        license_ = cls(
            doctor_id=doctor_id,
            license_number=license_number,
            issuing_authority=issuing_authority,
            country=country,
            issue_date=issue_date,
            expiry_date=expiry_date,
        )
        license_.record_event(
            DoctorLicenseAdded(
                license_id=license_.id,
                doctor_id=doctor_id,
                license_number=license_.license_number,
            )
        )
        return license_

    def is_expired(self, *, today: date) -> bool:
        return self.expiry_date < today

    def verify(self) -> None:
        if self.verification_status is LicenseVerificationStatus.VERIFIED:
            return
        self.verification_status = LicenseVerificationStatus.VERIFIED
        self.touch()
        self.record_event(DoctorLicenseVerified(license_id=self.id, doctor_id=self.doctor_id))

    def reject(self) -> None:
        if self.verification_status is LicenseVerificationStatus.REJECTED:
            return
        self.verification_status = LicenseVerificationStatus.REJECTED
        self.touch()
        self.record_event(DoctorLicenseRejected(license_id=self.id, doctor_id=self.doctor_id))


@dataclass(kw_only=True, eq=False)
class DoctorSpecialization(AggregateRoot):
    organization_id: UUID
    doctor_id: UUID
    specialization_name: str
    is_primary: bool = False
    years_of_experience: int = 0

    def __post_init__(self) -> None:
        if not self.specialization_name or not self.specialization_name.strip():
            raise SpecializationNameRequiredError()
        self.specialization_name = self.specialization_name.strip()
        _validate_years_of_experience(self.years_of_experience)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        doctor_id: UUID,
        specialization_name: str,
        is_primary: bool = False,
        years_of_experience: int = 0,
    ) -> "DoctorSpecialization":
        specialization = cls(
            organization_id=organization_id,
            doctor_id=doctor_id,
            specialization_name=specialization_name,
            is_primary=is_primary,
            years_of_experience=years_of_experience,
        )
        specialization.record_event(
            DoctorSpecializationAdded(
                specialization_id=specialization.id,
                doctor_id=doctor_id,
                specialization_name=specialization.specialization_name,
                is_primary=is_primary,
            )
        )
        return specialization


@dataclass(kw_only=True, eq=False)
class DoctorSchedule(AggregateRoot):
    """A doctor's own recurring weekly availability window (day, start/end
    time, optional break).

    **Deprecated in favor of `app.modules.schedule.domain.entities
    .DoctorSchedule`.** The two classes share a name but not a shape: this
    one has no `organization_id` and no slot-duration concept, so it
    cannot support tenant-scoped queries or appointment-slot generation.
    `app.modules.schedule`'s version is now the architecturally canonical,
    go-forward owner of "doctor schedule/availability" — see
    `docs/backend-architecture/14_doctor_schedule_ownership.md` for the
    full decision record.

    Retained completely unchanged (table, migration, repository, use
    case, and the two live `POST/GET /doctors/{doctor_id}/schedule`
    endpoints) rather than removed: no confirmed zero-consumer guarantee
    exists for a public, already-shipped API, so removing it would risk
    breaking an external caller. New code should depend on
    `app.modules.schedule`'s `DoctorSchedule` instead.
    """

    doctor_id: UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    break_start: time | None = None
    break_end: time | None = None
    is_available: bool = True

    def __post_init__(self) -> None:
        if self.start_time >= self.end_time:
            raise InvalidScheduleTimeRangeError()
        if (self.break_start is None) != (self.break_end is None):
            raise InvalidBreakTimeError()
        if self.break_start is not None and self.break_end is not None:
            if self.break_start >= self.break_end:
                raise InvalidBreakTimeError()
            if self.break_start < self.start_time or self.break_end > self.end_time:
                raise InvalidBreakTimeError()

    @classmethod
    def create(
        cls,
        *,
        doctor_id: UUID,
        day_of_week: DayOfWeek,
        start_time: time,
        end_time: time,
        break_start: time | None = None,
        break_end: time | None = None,
        is_available: bool = True,
    ) -> "DoctorSchedule":
        schedule = cls(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            break_start=break_start,
            break_end=break_end,
            is_available=is_available,
        )
        schedule.record_event(
            DoctorScheduleAdded(
                schedule_id=schedule.id, doctor_id=doctor_id, day_of_week=day_of_week.value
            )
        )
        return schedule

    def overlaps_with(self, other: "DoctorSchedule") -> bool:
        """Pure time-range overlap check — the caller is responsible for
        first filtering to entries on the same `day_of_week` (this method
        deliberately doesn't check `day_of_week` itself, since "overlap" is
        purely a time-range concept once two entries are known to share a
        day)."""
        return self.start_time < other.end_time and other.start_time < self.end_time


def _validate_years_of_experience(years: int) -> None:
    if years < 0:
        raise InvalidYearsOfExperienceError(years)


def _validate_consultation_fee(fee: Decimal | None) -> None:
    if fee is not None and fee < 0:
        raise InvalidConsultationFeeError(fee)
