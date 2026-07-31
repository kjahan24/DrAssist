"""Repository interfaces — one per aggregate root, expressed in domain
vocabulary only (no session, no SQL). Concrete implementations live in
`app.modules.organization.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.organization.domain.entities import Department, Organization, OrganizationSettings
from app.modules.organization.domain.enums import DepartmentStatus


class OrganizationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, organization_id: UUID) -> Organization | None: ...

    @abstractmethod
    async def get_by_code(self, organization_code: str) -> Organization | None: ...

    @abstractmethod
    async def list_active(self, *, offset: int = 0, limit: int = 20) -> list[Organization]: ...

    @abstractmethod
    async def add(self, organization: Organization) -> None: ...


class OrganizationSettingsRepository(ABC):
    @abstractmethod
    async def get_by_organization_id(
        self, organization_id: UUID
    ) -> OrganizationSettings | None: ...

    @abstractmethod
    async def add(self, settings: OrganizationSettings) -> None: ...


class DepartmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, department_id: UUID) -> Department | None: ...

    @abstractmethod
    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Department]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[DepartmentStatus] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Department], int]:
        """Search & Filtering module: organization-scoped search over
        departments — the Organization module's own searchable child
        collection (the app is single-tenant-per-request: a caller only
        ever sees their own organization, so "search organizations" in
        practice means searching *within* one, i.e. its departments).
        `query` combines full-text search over `name`/`description` with
        a partial match on `name`. Returns `(page_of_departments,
        total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, department: Department) -> None: ...
