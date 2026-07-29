"""`MarkLabOrderCollected` (Ordered -> Collected).

Gated by `ClinicalNoteQueryPort.is_editable` (a status transition is
still a write to the lab order) and `LabOrder.mark_collected()`'s own
precondition (`status` must currently be `Ordered` — raises
`CollectionRequiresOrderedLabOrderError` otherwise). Not gated by
`ensure_editable()`/`LabOrderNotEditableError`: "Ordered Lab Orders
become read-only" governs the *content* fields
(`priority`/`clinical_information`/`notes`/items), not the status
transitions that necessarily happen *after* an order becomes read-only —
the same split `app.modules.clinical_notes.domain.entities.ClinicalNote`
already draws between `update_details()` (Draft-only) and
`sign()`/`lock()` (each with its own distinct precondition).
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_orders.application.dto import LabOrderStatusOutput, MarkLabOrderCollectedInput
from app.modules.lab_orders.domain.exceptions import LabOrderNotFoundError
from app.modules.lab_orders.domain.repositories import LabOrderRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class MarkLabOrderCollected(UseCase[MarkLabOrderCollectedInput, LabOrderStatusOutput]):
    def __init__(
        self,
        *,
        lab_order_repository: LabOrderRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._lab_orders = lab_order_repository
        self._clinical_notes = clinical_note_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: MarkLabOrderCollectedInput) -> LabOrderStatusOutput:
        lab_order = await self._lab_orders.get_by_id(input_dto.lab_order_id)
        if lab_order is None:
            raise LabOrderNotFoundError(input_dto.lab_order_id)

        if not await self._clinical_notes.is_editable(lab_order.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        lab_order.mark_collected()
        await self._lab_orders.add(lab_order)
        self._uow.collect_events(lab_order.pull_events())
        await self._uow.commit()

        return LabOrderStatusOutput(
            lab_order_id=lab_order.id,
            clinical_note_id=lab_order.clinical_note_id,
            status=lab_order.status,
        )
