"""In-memory test doubles for the Appointment module's repository, Unit
of Work, and the four peer modules' public ports `CreateAppointment`/
`CompleteAppointment` depend on (via `AppointmentConsistencyService`) —
each implements the exact same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus
from app.modules.appointment.domain.repositories import AppointmentRepository
from app.modules.authentication.application.dto import UserSummaryDTO
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.doctor.application.dto import DoctorSummaryDTO
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.application.dto import PatientSummaryDTO
from app.modules.patient.domain.enums import Gender, PatientStatus
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

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[AppointmentStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        appointment_date_from: date | None = None,
        appointment_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "appointment_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Appointment], int]:
        matches = [a for a in self._appointments.values() if a.organization_id == organization_id]
        if statuses:
            matches = [a for a in matches if a.status in statuses]
        if patient_id is not None:
            matches = [a for a in matches if a.patient_id == patient_id]
        if doctor_id is not None:
            matches = [a for a in matches if a.doctor_id == doctor_id]
        if appointment_date_from is not None:
            matches = [a for a in matches if a.appointment_date >= appointment_date_from]
        if appointment_date_to is not None:
            matches = [a for a in matches if a.appointment_date <= appointment_date_to]
        if created_from is not None:
            matches = [a for a in matches if a.created_at >= created_from]
        if created_to is not None:
            matches = [a for a in matches if a.created_at <= created_to]
        if updated_from is not None:
            matches = [a for a in matches if a.updated_at >= updated_from]
        if updated_to is not None:
            matches = [a for a in matches if a.updated_at <= updated_to]
        if query:
            term = query.strip().lower()
            matches = [
                a
                for a in matches
                if term in a.appointment_number.lower()
                or (a.reason_for_visit is not None and term in a.reason_for_visit.lower())
                or (a.notes is not None and term in a.notes.lower())
            ]
        matches.sort(key=lambda a: getattr(a, sort_by, None) or "", reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

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
        "gender": Gender.FEMALE,
        "date_of_birth": date(1990, 1, 1),
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
        "joining_date": date(2020, 1, 1),
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
