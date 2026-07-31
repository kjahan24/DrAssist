"""Repository interface for the `PatientVisit` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation lives
in `app.modules.visit.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.enums import VisitStatus


class PatientVisitRepository(ABC):
    @abstractmethod
    async def get_by_id(self, visit_id: UUID) -> PatientVisit | None: ...

    @abstractmethod
    async def get_by_visit_number(
        self, *, organization_id: UUID, visit_number: str
    ) -> PatientVisit | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientVisit]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[VisitStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_date_from: date | None = None,
        visit_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "visit_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[PatientVisit], int]:
        """Search & Filtering module: organization-scoped search over
        patient visits — `query` combines full-text search
        (`chief_complaint_summary`/`reason_for_visit`/`notes`) with a
        partial match on `visit_number`; `patient_id`/`doctor_id` are
        exact-match UUID filters. Returns `(page_of_visits,
        total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, visit: PatientVisit) -> None: ...
