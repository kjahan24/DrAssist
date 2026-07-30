"""Domain exceptions for the Appointment module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`PatientNotFoundError`/`DoctorNotFoundError`/`BookedByUserNotFoundError`/
`AppointmentVisitNotFoundError` are defined locally rather than reused
from their owning modules — the same situation every prior child-document
module documents: none of `app.modules.patient`, `app.modules.doctor`,
`app.modules.authentication`, or `app.modules.visit` expose a "not found"
error a peer module is allowed to import, so a module that *references*
an existing row by id defines the exception locally.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class PatientNotFoundError(DomainError):
    def __init__(self, patient_id: UUID) -> None:
        super().__init__(f"no patient found with id {patient_id}")
        self.patient_id = patient_id


class DoctorNotFoundError(DomainError):
    def __init__(self, doctor_id: UUID) -> None:
        super().__init__(f"no doctor found with id {doctor_id}")
        self.doctor_id = doctor_id


class PatientDoctorOrganizationMismatchError(DomainError):
    def __init__(self, patient_id: UUID, doctor_id: UUID) -> None:
        super().__init__(
            f"patient {patient_id} and doctor {doctor_id} do not belong to the same organization"
        )
        self.patient_id = patient_id
        self.doctor_id = doctor_id


class BookedByUserNotFoundError(DomainError):
    def __init__(self, booked_by_user_id: UUID) -> None:
        super().__init__(f"no user found with id {booked_by_user_id}")
        self.booked_by_user_id = booked_by_user_id


class BookedByUserOrganizationMismatchError(DomainError):
    def __init__(self, booked_by_user_id: UUID, organization_id: UUID) -> None:
        super().__init__(
            f"user {booked_by_user_id} does not belong to organization {organization_id}"
        )
        self.booked_by_user_id = booked_by_user_id
        self.organization_id = organization_id


class AppointmentVisitNotFoundError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(f"no visit found with id {visit_id}")
        self.visit_id = visit_id


class AppointmentVisitMismatchError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(
            f"visit {visit_id} does not belong to the same organization/patient/doctor as "
            "this appointment"
        )
        self.visit_id = visit_id


class AppointmentNotFoundError(DomainError):
    def __init__(self, appointment_id: UUID) -> None:
        super().__init__(f"no appointment found with id {appointment_id}")
        self.appointment_id = appointment_id


class AppointmentNumberRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("appointment_number must not be blank")


class DuplicateAppointmentNumberError(DomainError):
    def __init__(self, appointment_number: str) -> None:
        super().__init__(f"appointment_number {appointment_number!r} is already in use")
        self.appointment_number = appointment_number


class InvalidAppointmentTimeRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("end_time must be later than start_time")


class AppointmentNotEditableError(DomainError):
    def __init__(self) -> None:
        super().__init__("completed or no-show appointments cannot be modified")


class InvalidAppointmentStatusTransitionError(DomainError):
    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(f"cannot transition appointment from {current_status} to {target_status}")
        self.current_status = current_status
        self.target_status = target_status
