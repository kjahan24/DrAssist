"""Domain exceptions for the Schedule/Availability module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`DoctorNotFoundError` is defined locally rather than reused from
`app.modules.doctor.domain.exceptions` — the same situation every prior
child-document module documents: `app.modules.doctor` exposes no "not
found" error a peer module is allowed to import, so a module that
*references* an existing row by id defines the exception locally.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class DoctorNotFoundError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        super().__init__(f"no doctor found with id {doctor_id}")
        self.doctor_id = doctor_id


class DoctorScheduleNotFoundError(DomainError):
    def __init__(self, schedule_id: UUID) -> None:
        super().__init__(f"no doctor schedule found with id {schedule_id}")
        self.schedule_id = schedule_id


class InvalidScheduleTimeRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("end_time must be later than start_time")


class InvalidSlotDurationError(DomainError):
    def __init__(self) -> None:
        super().__init__("slot_duration_minutes must be greater than zero")


class DoctorScheduleOverlapError(DomainError):
    def __init__(self, doctor_id: UUID, weekday: str) -> None:
        super().__init__(f"doctor {doctor_id} already has an overlapping schedule on {weekday}")
        self.doctor_id = doctor_id
        self.weekday = weekday


class DoctorTimeOffNotFoundError(DomainError):
    def __init__(self, time_off_id: UUID) -> None:
        super().__init__(f"no doctor time-off period found with id {time_off_id}")
        self.time_off_id = time_off_id


class InvalidTimeOffRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("end_datetime must be later than start_datetime")


class DoctorTimeOffOverlapError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        super().__init__(f"doctor {doctor_id} already has an overlapping time-off period")
        self.doctor_id = doctor_id
