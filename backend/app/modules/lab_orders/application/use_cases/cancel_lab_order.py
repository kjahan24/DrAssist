"""`CancelLabOrder` (Draft|Ordered -> Cancelled) — "Cancelled orders
cannot be edited" implies a transition *into* Cancelled exists; this is
it.

Gated by `ClinicalNoteQueryPort.is_editable` and
`LabOrder.cancel()`'s own precondition (`status` must currently be
`Draft` or `Ordered` — raises `LabOrderCannotBeCancelledError` for an
already-`Collected` or already-`Cancelled` order, the same "not gated by
`ensure_editable()`" reasoning `mark_lab_order_collected.py` documents for
its own transition).
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_orders.application.dto import CancelLabOrderInput, LabOrderStatusOutput
from app.modules.lab_orders.domain.exceptions import LabOrderNotFoundError
from app.modules.lab_orders.domain.repositories import LabOrderRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CancelLabOrder(UseCase[CancelLabOrderInput, LabOrderStatusOutput]):
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

    async def execute(self, input_dto: CancelLabOrderInput) -> LabOrderStatusOutput:
        lab_order = await self._lab_orders.get_by_id(input_dto.lab_order_id)
        if lab_order is None:
            raise LabOrderNotFoundError(input_dto.lab_order_id)

        if not await self._clinical_notes.is_editable(lab_order.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        lab_order.cancel()
        await self._lab_orders.add(lab_order)
        self._uow.collect_events(lab_order.pull_events())
        await self._uow.commit()

        return LabOrderStatusOutput(
            lab_order_id=lab_order.id,
            clinical_note_id=lab_order.clinical_note_id,
            status=lab_order.status,
        )
