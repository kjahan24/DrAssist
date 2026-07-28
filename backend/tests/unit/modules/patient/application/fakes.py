"""In-memory test doubles for the Patient module's repository, Unit of
Work, and the Organization module's cross-module port `RegisterPatient`
depends on — each implements the exact same interface its real
counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database or another module's facade.
"""

from uuid import UUID

from app.modules.organization.public.dto import OrganizationSummaryDTO
from app.modules.organization.public.interfaces import OrganizationQueryPort
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.repositories import PatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakePatientRepository(PatientRepository):
    def __init__(self) -> None:
        self._patients: dict[UUID, Patient] = {}

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        return self._patients.get(patient_id)

    async def get_by_patient_number(
        self, *, organization_id: UUID, patient_number: str
    ) -> Patient | None:
        for patient in self._patients.values():
            if (
                patient.organization_id == organization_id
                and patient.patient_number == patient_number.strip()
            ):
                return patient
        return None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Patient]:
        matches = [p for p in self._patients.values() if p.organization_id == organization_id]
        return matches[offset : offset + limit]

    async def add(self, patient: Patient) -> None:
        self._patients[patient.id] = patient


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


class FakeOrganizationQueryPort(OrganizationQueryPort):
    """Backed by a settable set of "existing" organization ids —
    `RegisterPatient` only calls `organization_exists`."""

    def __init__(self, *, existing_organization_ids: set[UUID] | None = None) -> None:
        self.existing_organization_ids = existing_organization_ids or set()

    async def organization_exists(self, organization_id: UUID) -> bool:
        return organization_id in self.existing_organization_ids

    async def is_active(self, organization_id: UUID) -> bool:
        return organization_id in self.existing_organization_ids

    async def get_organization_summary(
        self, organization_id: UUID
    ) -> OrganizationSummaryDTO | None:
        raise NotImplementedError("not exercised by any use case tested against this fake")

    async def get_default_timezone(self, organization_id: UUID) -> str | None:
        raise NotImplementedError("not exercised by any use case tested against this fake")
