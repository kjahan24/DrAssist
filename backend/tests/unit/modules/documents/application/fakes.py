"""In-memory test doubles for the Documents module's repository, Unit of
Work, `StoragePort`, and the Patient/Visit/Appointment modules'
cross-module ports the use cases depend on — each implements the exact
same interface its real counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database, real filesystem, or another module's
facade.
"""

from datetime import date, time
from typing import BinaryIO
from uuid import UUID, uuid4

from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.public.dto import AppointmentSummaryDTO
from app.modules.appointment.public.interfaces import AppointmentQueryPort
from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.modules.patient.domain.enums import Gender, PatientStatus
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort
from app.shared.application.storage_port import StoragePort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeMedicalDocumentRepository(MedicalDocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[UUID, MedicalDocument] = {}

    async def get_by_id(self, document_id: UUID) -> MedicalDocument | None:
        return self._documents.get(document_id)

    async def get_by_stored_filename(self, stored_filename: str) -> MedicalDocument | None:
        for document in self._documents.values():
            if document.stored_filename == stored_filename.strip():
                return document
        return None

    async def list_by_patient(self, patient_id: UUID) -> list[MedicalDocument]:
        matches = [d for d in self._documents.values() if d.patient_id == patient_id]
        return sorted(matches, key=lambda d: d.uploaded_at, reverse=True)

    async def list_by_visit(self, visit_id: UUID) -> list[MedicalDocument]:
        matches = [d for d in self._documents.values() if d.visit_id == visit_id]
        return sorted(matches, key=lambda d: d.uploaded_at, reverse=True)

    async def list_by_appointment(self, appointment_id: UUID) -> list[MedicalDocument]:
        matches = [d for d in self._documents.values() if d.appointment_id == appointment_id]
        return sorted(matches, key=lambda d: d.uploaded_at, reverse=True)

    async def add(self, document: MedicalDocument) -> None:
        self._documents[document.id] = document


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
    id — `UploadMedicalDocument` calls `get_patient_summary` both to
    check existence and to derive `organization_id`."""

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
            patient_number="PAT-0001",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
            status=PatientStatus.ACTIVE,
        )

    async def list_allergies_for_patient(self, patient_id: UUID) -> list[PatientAllergySummaryDTO]:
        return []

    async def list_medical_conditions_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicalConditionSummaryDTO]:
        return []


class FakeVisitQueryPort(VisitQueryPort):
    """Backed by a settable map of "existing" visit id -> (organization
    id, patient id) — `UploadMedicalDocument` checks both against the
    document's own `organization_id`/`patient_id` for "visit ownership"."""

    def __init__(self, *, existing_visits: dict[UUID, tuple[UUID, UUID]] | None = None) -> None:
        self.existing_visits = existing_visits or {}

    async def visit_exists(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def is_active(self, visit_id: UUID) -> bool:
        return visit_id in self.existing_visits

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        pair = self.existing_visits.get(visit_id)
        if pair is None:
            return None
        organization_id, patient_id = pair
        return VisitSummaryDTO(
            visit_id=visit_id,
            organization_id=organization_id,
            patient_id=patient_id,
            doctor_id=uuid4(),
            visit_number="V-0001",
            visit_status=VisitStatus.SCHEDULED,
        )

    async def list_visits_for_patient(self, patient_id: UUID) -> list[VisitSummaryDTO]:
        return []


class FakeAppointmentQueryPort(AppointmentQueryPort):
    """Backed by a settable map of "existing" appointment id ->
    (organization id, patient id) — `UploadMedicalDocument` checks both
    against the document's own `organization_id`/`patient_id` for
    "appointment ownership"."""

    def __init__(
        self, *, existing_appointments: dict[UUID, tuple[UUID, UUID]] | None = None
    ) -> None:
        self.existing_appointments = existing_appointments or {}

    async def appointment_exists(self, appointment_id: UUID) -> bool:
        return appointment_id in self.existing_appointments

    async def is_editable(self, appointment_id: UUID) -> bool:
        return appointment_id in self.existing_appointments

    async def get_appointment_summary(self, appointment_id: UUID) -> AppointmentSummaryDTO | None:
        pair = self.existing_appointments.get(appointment_id)
        if pair is None:
            return None
        organization_id, patient_id = pair
        return AppointmentSummaryDTO(
            appointment_id=appointment_id,
            organization_id=organization_id,
            patient_id=patient_id,
            doctor_id=uuid4(),
            appointment_number="APT-0001",
            appointment_date=date(2026, 1, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
            status=AppointmentStatus.SCHEDULED,
            reason_for_visit=None,
            notes=None,
            booked_by_user_id=None,
            visit_id=None,
            checked_in_at=None,
            completed_at=None,
            cancelled_at=None,
        )

    async def get_by_appointment_number(
        self, appointment_number: str
    ) -> AppointmentSummaryDTO | None:
        return None

    async def list_appointments_for_patient(self, patient_id: UUID) -> list[AppointmentSummaryDTO]:
        return []

    async def list_appointments_for_doctor(self, doctor_id: UUID) -> list[AppointmentSummaryDTO]:
        return []


class FakeStoragePort(StoragePort):
    """In-memory `(bucket, object_name) -> bytes` store."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def upload(
        self, *, bucket: str, object_name: str, data: BinaryIO, content_type: str
    ) -> str:
        self.objects[(bucket, object_name)] = data.read()
        return object_name

    async def download(self, *, bucket: str, object_name: str) -> bytes:
        try:
            return self.objects[(bucket, object_name)]
        except KeyError as exc:
            raise FileNotFoundError(f"no object found at {bucket}/{object_name}") from exc

    async def delete(self, *, bucket: str, object_name: str) -> None:
        self.objects.pop((bucket, object_name), None)

    async def get_presigned_url(
        self, *, bucket: str, object_name: str, expires_seconds: int = 3600
    ) -> str:
        raise NotImplementedError
