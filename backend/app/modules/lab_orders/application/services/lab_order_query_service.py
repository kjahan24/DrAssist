"""Read-only queries against `LabOrder`/`LabOrderItem`.

Backs the module's public `LabOrderQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

Shaped like `app.modules.clinical_notes.application.services
.clinical_note_query_service.ClinicalNoteQueryService`, not
`app.modules.prescriptions.application.services
.prescription_query_service.PrescriptionQueryService`: `LabOrder` is
one-to-*many* with `ClinicalNote` ("One Clinical Note may contain
multiple Lab Orders"), so `list_lab_orders_for_clinical_note` — not a
single `get_..._summary(clinical_note_id)` — is the query keyed by
clinical note; `get_lab_order_summary` is instead keyed by the lab
order's own id. `is_editable` mirrors
`ClinicalNoteQueryService.is_editable`'s own boolean-not-enum shape, for
the identical reason: a future module (Lab Results, in particular) needs
to ask "can I still write to this lab order?" without importing
`LabOrderStatus` across the module boundary.

Depends on both repositories (like `PrescriptionQueryService`) because
`LabOrderSummaryDTO` embeds the full item list — this task's own Future
Compatibility list (LIS, HL7/FHIR, Lab Results, AI Lab Interpretation,
Clinical Decision Support, Notifications) all need the actual test data,
not just "an order exists".
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.lab_orders.application.dto import LabOrderItemSummaryDTO, LabOrderSummaryDTO
from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.domain.repositories import LabOrderItemRepository, LabOrderRepository

_NOT_EDITABLE_STATUSES = frozenset(
    {LabOrderStatus.ORDERED, LabOrderStatus.COLLECTED, LabOrderStatus.CANCELLED}
)


class LabOrderQueryService:
    def __init__(
        self,
        *,
        lab_order_repository: LabOrderRepository,
        lab_order_item_repository: LabOrderItemRepository,
    ) -> None:
        self._lab_orders = lab_order_repository
        self._items = lab_order_item_repository

    async def lab_order_exists(self, lab_order_id: UUID) -> bool:
        return await self._lab_orders.get_by_id(lab_order_id) is not None

    async def is_editable(self, lab_order_id: UUID) -> bool:
        lab_order = await self._lab_orders.get_by_id(lab_order_id)
        return lab_order is not None and lab_order.status not in _NOT_EDITABLE_STATUSES

    async def get_lab_order_summary(self, lab_order_id: UUID) -> LabOrderSummaryDTO | None:
        lab_order = await self._lab_orders.get_by_id(lab_order_id)
        if lab_order is None:
            return None
        return await self._to_summary(lab_order)

    async def list_lab_orders_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[LabOrderSummaryDTO]:
        lab_orders = await self._lab_orders.list_by_clinical_note(clinical_note_id)
        return [await self._to_summary(lab_order) for lab_order in lab_orders]

    async def list_lab_orders_for_patient(self, patient_id: UUID) -> list[LabOrderSummaryDTO]:
        lab_orders = await self._lab_orders.list_by_patient(patient_id)
        return [await self._to_summary(lab_order) for lab_order in lab_orders]

    async def search_lab_orders(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[LabOrderStatus] | None = None,
        priorities: Sequence[Priority] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        clinical_note_id: UUID | None = None,
        ordered_from: datetime | None = None,
        ordered_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "ordered_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[LabOrderSummaryDTO], int]:
        """Search & Filtering module — see `LabOrderRepository.search`'s
        docstring for filter/sort/pagination semantics, and
        `PrescriptionQueryService.search_prescriptions`'s docstring for
        the identical batch-item N+1-avoidance shape used here."""
        lab_orders, total = await self._lab_orders.search(
            organization_id=organization_id,
            query=query,
            statuses=statuses,
            priorities=priorities,
            patient_id=patient_id,
            doctor_id=doctor_id,
            visit_id=visit_id,
            clinical_note_id=clinical_note_id,
            ordered_from=ordered_from,
            ordered_to=ordered_to,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        items_by_order: dict[UUID, list[LabOrderItem]] = defaultdict(list)
        for item in await self._items.list_by_lab_orders([o.id for o in lab_orders]):
            items_by_order[item.lab_order_id].append(item)
        return [
            _build_summary(lab_order, items_by_order[lab_order.id]) for lab_order in lab_orders
        ], total

    async def _to_summary(self, lab_order: LabOrder) -> LabOrderSummaryDTO:
        items = await self._items.list_by_lab_order(lab_order.id)
        return _build_summary(lab_order, items)


def _build_summary(lab_order: LabOrder, items: Sequence[LabOrderItem]) -> LabOrderSummaryDTO:
    return LabOrderSummaryDTO(
        lab_order_id=lab_order.id,
        organization_id=lab_order.organization_id,
        clinical_note_id=lab_order.clinical_note_id,
        patient_id=lab_order.patient_id,
        visit_id=lab_order.visit_id,
        doctor_id=lab_order.doctor_id,
        order_number=lab_order.order_number,
        ordered_at=lab_order.ordered_at,
        priority=lab_order.priority,
        status=lab_order.status,
        clinical_information=lab_order.clinical_information,
        notes=lab_order.notes,
        items=[_to_item_summary(item) for item in items],
    )


def _to_item_summary(item: LabOrderItem) -> LabOrderItemSummaryDTO:
    return LabOrderItemSummaryDTO(
        lab_order_item_id=item.id,
        lab_order_id=item.lab_order_id,
        test_code=item.test_code,
        test_name=item.test_name,
        specimen_type=item.specimen_type,
        status=item.status,
        specimen_site=item.specimen_site,
        instructions=item.instructions,
    )
