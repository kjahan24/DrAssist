"""`AddLabOrderItem` — "One Lab Order contains multiple Lab Order Items" /
"Lab Order Items cannot exist without a Lab Order" (this task's own
Business Rules, expressed for `LabOrder` the way `app.modules
.prescriptions.application.use_cases.add_prescription_item
.AddPrescriptionItem`'s own docstring already documents for
`Prescription`).

`lab_order_id` on the created `LabOrderItem` is set from the `LabOrder`
this use case already loaded and validated — never accepted as
independent caller input — which is what satisfies "Ownership validation"
(this task's own Validation section) *by construction*.

Gated by the identical pair of checks `UpdateLabOrder` uses: the
cross-module "is the linked Clinical Note editable" check and this
aggregate's own `ensure_editable()`, since adding an item is content-
editing on an already-existing lab order, subject to the same "only Draft
is editable" rule as any other mutation.
"""

from app.modules.clinical_notes.public.exceptions import ClinicalNoteNotEditableError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_orders.application.dto import AddLabOrderItemInput, AddLabOrderItemOutput
from app.modules.lab_orders.domain.entities import LabOrderItem
from app.modules.lab_orders.domain.exceptions import LabOrderNotFoundError
from app.modules.lab_orders.domain.repositories import LabOrderItemRepository, LabOrderRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddLabOrderItem(UseCase[AddLabOrderItemInput, AddLabOrderItemOutput]):
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

    async def execute(self, input_dto: AddLabOrderItemInput) -> AddLabOrderItemOutput:
        lab_order = await self._lab_orders.get_by_id(input_dto.lab_order_id)
        if lab_order is None:
            raise LabOrderNotFoundError(input_dto.lab_order_id)

        lab_order.ensure_editable()
        if not await self._clinical_notes.is_editable(lab_order.clinical_note_id):
            raise ClinicalNoteNotEditableError()

        item = LabOrderItem.create(
            lab_order_id=lab_order.id,
            test_code=input_dto.test_code,
            test_name=input_dto.test_name,
            specimen_type=input_dto.specimen_type,
            specimen_site=input_dto.specimen_site,
            instructions=input_dto.instructions,
        )
        await self._items.add(item)
        self._uow.collect_events(item.pull_events())
        await self._uow.commit()

        return AddLabOrderItemOutput(lab_order_item_id=item.id, lab_order_id=lab_order.id)
