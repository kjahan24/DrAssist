"""In-memory test doubles for the Appointment module's repository, Unit
of Work, and the four peer modules' public ports `CreateAppointment`/
`CompleteAppointment` depend on (via `AppointmentConsistencyService`) —
each implements the exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID, uuid4

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.modules.authentication.application.dto import UserSummaryDTO
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.doctor.application.dto import DoctorSummaryDTO
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.application.dto import PatientSummaryDTO
from app.modules.patient.domain.enums import PatientStatus
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.application.dto import VisitSummaryDTO
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeAppointmentRepository(AppointmentRepository):
    def __init__(self) -> None:
        self._appointments: dict[UUID, Appointment] = {}

    async def get_by_id(self, appointment_id: UUID) -> Appointment | None:
        return self._appointments.get(appointment_id)

    async def get_by_appointment_number(self, appointment_number: str) -> Appointment | None:
        for appointment in self._appointments.values():
            if appointment.appointment_number == appointment_number:
                return appointment
        return None

    async def list_by_patient(self, patient_id: UUID) -> list[Appointment]:
        matches = [a for a in self._appointments.values() if a.patient_id == patient_id]
        return sorted(matches, key=lambda a: (a.appointment_date, a.start_time))

    async def list_by_doctor(self, doctor_id: UUID) -> list[Appointment]:
        matches = [a for a in self._appointments.values() if a.doctor_id == doctor_id]
        return sorted(matches, key=lambda a: (a.appointment_date, a.start_time))

    async def add(self, appointment: Appointment) -> None:
        self._appointments[appointment.id] = appointment


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass


class FakePatientQueryPort(PatientQueryPort):
    def __init__(self, *, existing_patients: dict[UUID, PatientSummaryDTO] | None = None) -> None:
        self.existing_patients = existing_patients or {}

    async def patient_exists(self, patient_id: UUID) -> bool:
        return patient_id in self.existing_patients

    async def is_active(self, patient_id: UUID) -> bool:
        return patient_id in self.existing_patients

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        return self.existing_patients.get(patient_id)


class FakeDoctorQueryPort(DoctorQueryPort):
    def __init__(self, *, existing_doctors: dict[UUID, DoctorSummaryDTO] | None = None) -> None:
        self.existing_doctors = existing_doctors or {}

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def is_active(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        return self.existing_doctors.get(doctor_id)


class FakeUserQueryPort(UserQueryPort):
    def __init__(self, *, existing_users: dict[UUID, UserSummaryDTO] | None = None) -> None:
        self.existing_users = existing_users or {}

    async def user_exists(self, user_id: UUID) -> bool:
        return user_id in self.existing_users

    async def get_user_summary(self, user_id: UUID) -> UserSummaryDTO | None:
        return self.existing_users.get(user_id)


class FakeVisitQueryPort(VisitQueryPort):
    def __init__(self, *, existing_visits: dict[UUID, VisitSummaryDTO] | None = None) -> None:
        self.existing_visits = existing_visits or {}

    async def visit_exists(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def is_active(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        return self.existing_visits.get(visit_id)


def make_patient_summary(**overrides: object) -> PatientSummaryDTO:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "organization_id": uuid4(),
        "patient_number": "PAT-0001",
        "first_name": "Jane",
        "last_name": "Doe",
        "status": PatientStatus.ACTIVE,
    }
    defaults.update(overrides)
    return PatientSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_doctor_summary(**overrides: object) -> DoctorSummaryDTO:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "employee_id": "EMP-0001",
        "status": DoctorStatus.ACTIVE,
    }
    defaults.update(overrides)
    return DoctorSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_user_summary(**overrides: object) -> UserSummaryDTO:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "email": "staff@example.com",
        "first_name": "Front",
        "last_name": "Desk",
        "status": UserStatus.ACTIVE,
    }
    defaults.update(overrides)
    return UserSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_visit_summary(**overrides: object) -> VisitSummaryDTO:
    defaults: dict[str, object] = {
        "visit_id": uuid4(),
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "visit_number": "V-0001",
        "visit_status": VisitStatus.IN_PROGRESS,
    }
    defaults.update(overrides)
    return VisitSummaryDTO(**defaults)  # type: ignore[arg-type]
