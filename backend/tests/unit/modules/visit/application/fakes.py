"""In-memory test doubles for the Visit module's repository, Unit of
Work, and the Patient/Doctor modules' cross-module ports `ScheduleVisit`
depends on — each implements the exact same interface its real
counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from datetime import date
from uuid import UUID, uuid4

from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.public.dto import DoctorSummaryDTO
from app.modules.doctor.public.interfaces import DoctorQueryPort
from app.modules.patient.domain.enums import Gender, PatientStatus
from app.modules.patient.public.dto import PatientSummaryDTO
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.repositories import PatientVisitRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakePatientVisitRepository(PatientVisitRepository):
    def __init__(self) -> None:
        self._visits: dict[UUID, PatientVisit] = {}

    async def get_by_id(self, visit_id: UUID) -> PatientVisit | None:
        return self._visits.get(visit_id)

    async def get_by_visit_number(
        self, *, organization_id: UUID, visit_number: str
    ) -> PatientVisit | None:
        for visit in self._visits.values():
            if (
                visit.organization_id == organization_id
                and visit.visit_number == visit_number.strip()
            ):
                return visit
        return None

    async def list_by_patient(self, patient_id: UUID) -> list[PatientVisit]:
        return [v for v in self._visits.values() if v.patient_id == patient_id]

    async def add(self, visit: PatientVisit) -> None:
        self._visits[visit.id] = visit


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
    """Backed by a settable map of "existing" patient id -> organization
    id — `ScheduleVisit` calls `get_patient_summary` both to check
    existence and to derive `organization_id`."""

    def __init__(self, *, existing_patients: dict[UUID, UUID] | None = None) -> None:
        self.existing_patients = existing_patients or {}

    async def patient_exists(self, patient_id: UUID) -> bool:
        return patient_id in self.existing_patients

    async def is_active(self, patient_id: UUID) -> bool:
        return patient_id in self.existing_patients

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        organization_id = self.existing_patients.get(patient_id)
        if organization_id is None:
            return None
        return PatientSummaryDTO(
            patient_id=patient_id,
            organization_id=organization_id,
            patient_number="PAT-001",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
            status=PatientStatus.ACTIVE,
        )


class FakeDoctorQueryPort(DoctorQueryPort):
    """Backed by a settable map of "existing" doctor id -> organization
    id — mirrors `FakePatientQueryPort`, since `ScheduleVisit` calls
    `get_doctor_summary` both to check existence and to confirm the
    doctor belongs to the same organization as the patient."""

    def __init__(self, *, existing_doctors: dict[UUID, UUID] | None = None) -> None:
        self.existing_doctors = existing_doctors or {}

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def is_active(self, doctor_id: UUID) -> bool:
        return doctor_id in self.existing_doctors

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        organization_id = self.existing_doctors.get(doctor_id)
        if organization_id is None:
            return None
        return DoctorSummaryDTO(
            doctor_id=doctor_id,
            organization_id=organization_id,
            user_id=uuid4(),
            employee_id="EMP-001",
            joining_date=date(2020, 1, 1),
            status=DoctorStatus.ACTIVE,
        )
