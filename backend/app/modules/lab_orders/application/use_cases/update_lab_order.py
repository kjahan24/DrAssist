"""`UpdateLabOrder` — gated by the identical pair of checks every mutating
Lab Orders use case shares: `ClinicalNoteQueryPort.is_editable` (the
cross-module "is the linked Clinical Note itself Signed/Locked" check —
raises the reused `ClinicalNoteNotEditableError`) and
`LabOrder.ensure_editable()` (this aggregate's own Draft-only self-check,
called internally by `update_details()` — raises
`LabOrderNotEditableError`). Only `priority`/`clinical_information`/
`notes` are mutable here; `order_number`/`ordered_at` and every identity
field are immutable once set — see `domain/entities.py`.
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_orders.application.dto import UpdateLabOrderInput, UpdateLabOrderOutput
from app.modules.lab_orders.domain.exceptions import LabOrderNotFoundError
from app.modules.lab_orders.domain.repositories import LabOrderRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateLabOrder(UseCase[UpdateLabOrderInput, UpdateLabOrderOutput]):
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

    async def execute(self, input_dto: UpdateLabOrderInput) -> UpdateLabOrderOutput:
        lab_order = await self._lab_orders.get_by_id(input_dto.lab_order_id)
        if lab_order is None:
            raise LabOrderNotFoundError(input_dto.lab_order_id)

        if not await self._clinical_notes.is_editable(lab_order.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        lab_order.update_details(
            priority=input_dto.priority,
            clinical_information=input_dto.clinical_information,
            notes=input_dto.notes,
        )
        await self._lab_orders.add(lab_order)
        self._uow.collect_events(lab_order.pull_events())
        await self._uow.commit()

        return UpdateLabOrderOutput(
            lab_order_id=lab_order.id, clinical_note_id=lab_order.clinical_note_id
        )
