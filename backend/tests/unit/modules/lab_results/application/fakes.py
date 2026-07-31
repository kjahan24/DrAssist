"""In-memory test doubles for the Lab Results module's repositories, Unit
of Work, and the Lab Orders module's public port the use cases depend
on — each implements the exact same interface its real counterpart does,
per `docs/backend-architecture/12_testing_architecture.md` ("fakes over
mocks as the default"). Application-layer use case/service tests depend
on these, never on a real database or another module's facade.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.public.dto import LabOrderItemSummaryDTO, LabOrderSummaryDTO
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.enums import LabResultStatus
from app.modules.lab_results.domain.repositories import (
    LabResultItemRepository,
    LabResultRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeLabResultRepository(LabResultRepository):
    def __init__(self) -> None:
        self._lab_results: dict[UUID, LabResult] = {}

    async def get_by_id(self, lab_result_id: UUID) -> LabResult | None:
        return self._lab_results.get(lab_result_id)

    async def get_by_lab_order_id(self, lab_order_id: UUID) -> LabResult | None:
        for lab_result in self._lab_results.values():
            if lab_result.lab_order_id == lab_order_id:
                return lab_result
        return None

    async def get_by_result_number(self, result_number: str) -> LabResult | None:
        for lab_result in self._lab_results.values():
            if lab_result.result_number == result_number.strip():
                return lab_result
        return None

    async def list_by_patient(self, patient_id: UUID) -> list[LabResult]:
        matches = [r for r in self._lab_results.values() if r.patient_id == patient_id]
        return sorted(matches, key=lambda r: r.created_at)

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[LabResultStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        lab_order_id: UUID | None = None,
        reported_from: datetime | None = None,
        reported_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "reported_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[LabResult], int]:
        matches = [r for r in self._lab_results.values() if r.organization_id == organization_id]
        if statuses:
            matches = [r for r in matches if r.status in statuses]
        if patient_id is not None:
            matches = [r for r in matches if r.patient_id == patient_id]
        if doctor_id is not None:
            matches = [r for r in matches if r.doctor_id == doctor_id]
        if visit_id is not None:
            matches = [r for r in matches if r.visit_id == visit_id]
        if lab_order_id is not None:
            matches = [r for r in matches if r.lab_order_id == lab_order_id]
        if reported_from is not None:
            matches = [r for r in matches if r.reported_at >= reported_from]
        if reported_to is not None:
            matches = [r for r in matches if r.reported_at <= reported_to]
        if created_from is not None:
            matches = [r for r in matches if r.created_at >= created_from]
        if created_to is not None:
            matches = [r for r in matches if r.created_at <= created_to]
        if updated_from is not None:
            matches = [r for r in matches if r.updated_at >= updated_from]
        if updated_to is not None:
            matches = [r for r in matches if r.updated_at <= updated_to]
        if query:
            term = query.strip().lower()
            matches = [
                r
                for r in matches
                if term in r.result_number.lower()
                or (r.laboratory_name is not None and term in r.laboratory_name.lower())
                or (r.comments is not None and term in r.comments.lower())
            ]
        matches.sort(key=lambda r: getattr(r, sort_by, None) or "", reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, lab_result: LabResult) -> None:
        self._lab_results[lab_result.id] = lab_result


class FakeLabResultItemRepository(LabResultItemRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, LabResultItem] = {}

    async def get_by_id(self, lab_result_item_id: UUID) -> LabResultItem | None:
        return self._items.get(lab_result_item_id)

    async def list_by_lab_result(self, lab_result_id: UUID) -> list[LabResultItem]:
        matches = [i for i in self._items.values() if i.lab_result_id == lab_result_id]
        return sorted(matches, key=lambda i: i.created_at)

    async def list_by_lab_results(self, lab_result_ids: Sequence[UUID]) -> list[LabResultItem]:
        ids = set(lab_result_ids)
        matches = [i for i in self._items.values() if i.lab_result_id in ids]
        return sorted(matches, key=lambda i: i.created_at)

    async def add(self, item: LabResultItem) -> None:
        self._items[item.id] = item


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


class FakeLabOrderQueryPort(LabOrderQueryPort):
    """Backed by a settable map of "existing" lab order id -> summary
    (itself carrying whatever `LabOrderItemSummaryDTO`s the test wants to
    treat as valid references). `CreateLabResult`/`AddLabResultItem` call
    `get_lab_order_summary` to check existence, derive identity fields,
    and validate `lab_order_item_id` references."""

    def __init__(self, *, existing_orders: dict[UUID, LabOrderSummaryDTO] | None = None) -> None:
        self.existing_orders = existing_orders or {}

    async def lab_order_exists(self, lab_order_id: UUID) -> bool:
        return lab_order_id in self.existing_orders

    async def is_editable(self, lab_order_id: UUID) -> bool:
        order = self.existing_orders.get(lab_order_id)
        return order is not None and order.status is LabOrderStatus.DRAFT

    async def get_lab_order_summary(self, lab_order_id: UUID) -> LabOrderSummaryDTO | None:
        return self.existing_orders.get(lab_order_id)

    async def list_lab_orders_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[LabOrderSummaryDTO]:
        return [o for o in self.existing_orders.values() if o.clinical_note_id == clinical_note_id]

    async def list_lab_orders_for_patient(self, patient_id: UUID) -> list[LabOrderSummaryDTO]:
        return [o for o in self.existing_orders.values() if o.patient_id == patient_id]


def make_lab_order_item_summary(**overrides: object) -> LabOrderItemSummaryDTO:
    defaults: dict[str, object] = {
        "lab_order_item_id": uuid4(),
        "lab_order_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "specimen_type": "Blood",
        "status": LabOrderStatus.ORDERED,
        "specimen_site": None,
        "instructions": None,
    }
    defaults.update(overrides)
    return LabOrderItemSummaryDTO(**defaults)  # type: ignore[arg-type]


def make_lab_order_summary(**overrides: object) -> LabOrderSummaryDTO:
    defaults: dict[str, object] = {
        "lab_order_id": uuid4(),
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "order_number": "LAB-0001",
        "ordered_at": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        "priority": Priority.ROUTINE,
        "status": LabOrderStatus.ORDERED,
        "clinical_information": None,
        "notes": None,
        "items": [],
    }
    defaults.update(overrides)
    return LabOrderSummaryDTO(**defaults)  # type: ignore[arg-type]
