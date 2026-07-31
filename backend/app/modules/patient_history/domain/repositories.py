"""Repository interface for the `PatientHistory` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.patient_history.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method — the same reason every other repository in this
codebase lacks one (a repository returns the actual aggregate object and
the Unit of Work persists mutations through SQLAlchemy's session-level
change tracking), made doubly true here since `PatientHistory` itself
has no mutator to call in the first place.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType


class PatientHistoryRepository(ABC):
    @abstractmethod
    async def get_by_id(self, patient_history_id: UUID) -> PatientHistory | None: ...

    @abstractmethod
    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistory | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientHistory]: ...

    @abstractmethod
    async def list_by_visit(self, visit_id: UUID) -> list[PatientHistory]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        history_types: Sequence[HistoryType] | None = None,
        reference_types: Sequence[ReferenceType] | None = None,
        patient_id: UUID | None = None,
        visit_id: UUID | None = None,
        doctor_review_id: UUID | None = None,
        reference_id: UUID | None = None,
        encounter_date_from: date | None = None,
        encounter_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[PatientHistory], int]:
        """Search & Filtering module: organization-scoped search over
        patient history — `query` is a full-text match over `summary`;
        `reference_type` + `reference_id` together are also this
        endpoint's answer to the router's own long-standing note that
        `get_by_reference` should be "exposed as a query-parameter search
        on the list endpoint" — see `app.modules.patient_history.api
        .router`. Returns `(page_of_history, total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, history: PatientHistory) -> None: ...
