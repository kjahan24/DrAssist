"""`PlaceLabOrder` (Draft -> Ordered) — "Ordered Lab Orders must contain
at least one Lab Order Item", the one invariant in this module that spans
two separate aggregates.

Because `LabOrderItem` is its own top-level aggregate rather than an
in-memory child of `LabOrder` (see `domain/entities.py` for why), this use
case is the *only* place "at least one item" can be checked: it loads the
item list via `LabOrderItemRepository.list_by_lab_order` and raises
`LabOrderRequiresAtLeastOneItemError` before ever calling
`LabOrder.place_order()` — the identical reasoning
`app.modules.prescriptions.application.use_cases.finalize_prescription
.FinalizePrescription` already applies to its own cross-aggregate check.

Also gated by `ClinicalNoteQueryPort.is_editable` (placing the order is
itself a write) and `LabOrder.ensure_editable()` (an order that is no
longer Draft cannot be re-placed).
"""

from app.modules.clinical_notes.public.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_orders.application.dto import LabOrderStatusOutput, PlaceLabOrderInput
from app.modules.lab_orders.domain.exceptions import (
    LabOrderNotFoundError,
    LabOrderRequiresAtLeastOneItemError,
)
from app.modules.lab_orders.domain.repositories import LabOrderItemRepository, LabOrderRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class PlaceLabOrder(UseCase[PlaceLabOrderInput, LabOrderStatusOutput]):
    def __init__(
        self,
        *,
        lab_order_repository: LabOrderRepository,
        lab_order_item_repository: LabOrderItemRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._lab_orders = lab_order_repository
        self._items = lab_order_item_repository
        self._clinical_notes = clinical_note_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: PlaceLabOrderInput) -> LabOrderStatusOutput:
        lab_order = await self._lab_orders.get_by_id(input_dto.lab_order_id)
        if lab_order is None:
            raise LabOrderNotFoundError(input_dto.lab_order_id)

        if not await self._clinical_notes.is_editable(lab_order.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        items = await self._items.list_by_lab_order(lab_order.id)
        if not items:
            raise LabOrderRequiresAtLeastOneItemError(lab_order.id)

        lab_order.place_order()
        await self._lab_orders.add(lab_order)
        self._uow.collect_events(lab_order.pull_events())
        await self._uow.commit()

        return LabOrderStatusOutput(
            lab_order_id=lab_order.id,
            clinical_note_id=lab_order.clinical_note_id,
            status=lab_order.status,
        )
