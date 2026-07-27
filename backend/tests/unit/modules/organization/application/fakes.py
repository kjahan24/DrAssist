"""In-memory test doubles for the Organization module's repositories and
Unit of Work — each implements the exact same interface its real
SQLAlchemy counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer use case/service tests depend on
these, never on a real database.
"""

from uuid import UUID

from app.modules.organization.domain.entities import Department, Organization, OrganizationSettings
from app.modules.organization.domain.repositories import (
    DepartmentRepository,
    OrganizationRepository,
    OrganizationSettingsRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeOrganizationRepository(OrganizationRepository):
    def __init__(self) -> None:
        self._organizations: dict[UUID, Organization] = {}

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self._organizations.get(organization_id)

    async def get_by_code(self, organization_code: str) -> Organization | None:
        normalized = organization_code.strip().upper()
        for organization in self._organizations.values():
            if str(organization.organization_code) == normalized:
                return organization
        return None

    async def list_active(self, *, offset: int = 0, limit: int = 20) -> list[Organization]:
        matches = [o for o in self._organizations.values() if o.is_active]
        return matches[offset : offset + limit]

    async def add(self, organization: Organization) -> None:
        self._organizations[organization.id] = organization


class FakeOrganizationSettingsRepository(OrganizationSettingsRepository):
    def __init__(self) -> None:
        self._settings: dict[UUID, OrganizationSettings] = {}

    async def get_by_organization_id(self, organization_id: UUID) -> OrganizationSettings | None:
        for settings in self._settings.values():
            if settings.organization_id == organization_id:
                return settings
        return None

    async def add(self, settings: OrganizationSettings) -> None:
        self._settings[settings.id] = settings


class FakeDepartmentRepository(DepartmentRepository):
    def __init__(self) -> None:
        self._departments: dict[UUID, Department] = {}

    async def get_by_id(self, department_id: UUID) -> Department | None:
        return self._departments.get(department_id)

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Department]:
        matches = [d for d in self._departments.values() if d.organization_id == organization_id]
        return matches[offset : offset + limit]

    async def add(self, department: Department) -> None:
        self._departments[department.id] = department


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
