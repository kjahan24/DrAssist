"""Domain exceptions for the Doctor module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.
"""

from uuid import UUID

from app.modules.doctor.domain.enums import DayOfWeek
from app.shared.domain.exceptions import DomainError


class EmployeeIdRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("employee_id must not be blank")


class DuplicateEmployeeIdError(DomainError):
    def __init__(self, organization_id: UUID, employee_id: str) -> None:
        super().__init__(
            f"employee_id {employee_id!r} already exists in organization {organization_id}"
        )
        self.organization_id = organization_id
        self.employee_id = employee_id


class DoctorNotFoundError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        super().__init__(f"no doctor found with id {doctor_id}")
        self.doctor_id = doctor_id


class UserAlreadyHasDoctorProfileError(DomainError):
    """A `User` may back at most one `Doctor` — see `container.py`."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"user {user_id} already has a doctor profile")
        self.user_id = user_id


class DoctorProfileNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("full_name must not be blank")


class DoctorProfileNotFoundError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        super().__init__(f"no profile found for doctor {doctor_id}")
        self.doctor_id = doctor_id


class InvalidYearsOfExperienceError(DomainError):
    def __init__(self, years: int) -> None:
        super().__init__(f"years_of_experience must not be negative, got {years}")
        self.years = years


class InvalidConsultationFeeError(DomainError):
    def __init__(self, fee: object) -> None:
        super().__init__(f"consultation_fee must not be negative, got {fee}")
        self.fee = fee


class LicenseNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("license_number must not be blank")


class DuplicateLicenseNumberError(DomainError):
    def __init__(self, license_number: str) -> None:
        super().__init__(f"a license with number {license_number!r} already exists")
        self.license_number = license_number


class InvalidLicenseDateRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("expiry_date must be after issue_date")


class DoctorLicenseNotFoundError(DomainError):
    def __init__(self, license_id: UUID) -> None:
        super().__init__(f"no license found with id {license_id}")
        self.license_id = license_id


class SpecializationNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("specialization_name must not be blank")


class DoctorSpecializationNotFoundError(DomainError):
    def __init__(self, specialization_id: UUID) -> None:
        super().__init__(f"no specialization found with id {specialization_id}")
        self.specialization_id = specialization_id


class InvalidScheduleTimeRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("start_time must be before end_time")


class InvalidBreakTimeError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "break_start and break_end must both be set (or both unset) and fall within "
            "the shift's start_time/end_time, with break_start before break_end"
        )


class ScheduleOverlapError(DomainError):
    def __init__(self, doctor_id: UUID, day_of_week: DayOfWeek) -> None:
        super().__init__(
            f"doctor {doctor_id} already has an overlapping schedule entry on "
            f"{day_of_week.value}"
        )
        self.doctor_id = doctor_id
        self.day_of_week = day_of_week


class DoctorScheduleNotFoundError(DomainError):
    def __init__(self, schedule_id: UUID) -> None:
        super().__init__(f"no schedule entry found with id {schedule_id}")
        self.schedule_id = schedule_id
