"""`AddLabResultItem` — "One Lab Result contains multiple Lab Result
Items" / "Lab Result Items cannot exist without a Lab Result" (this
task's own Business Rules, expressed the way
`app.modules.prescriptions.application.use_cases.add_prescription_item
.AddPrescriptionItem`'s own docstring already documents for
`Prescription`).

Also enforces the one invariant unique to this module: "Every Lab Result
Item must reference an existing Lab Order Item." This requires
`LabOrderQueryPort` — the referenced `lab_order_item_id` must appear among
the *parent `LabOrder`*'s own items (fetched via
`get_lab_order_summary(lab_result.lab_order_id).items`) — so it is
checked here, at the application layer, the only place with I/O access
to both modules. A reference to an item that doesn't belong to this lab
result's own lab order raises `InvalidLabOrderItemReferenceError`.

`lab_result_id` on the created `LabResultItem` is set from the
`LabResult` this use case already loaded and validated — never accepted
as independent caller input — which is what satisfies "Ownership
validation" (this task's own Validation section) *by construction*.

Gated by `LabResult.ensure_editable()` alone (no cross-module
`is_editable` check — see `domain/entities.py`), since adding an item is
content-editing on an already-existing lab result, subject to the same
"only Draft is editable" rule as any other mutation.
"""

from app.modules.lab_orders.public.interfaces import LabOrderQueryPort
from app.modules.lab_results.application.dto import AddLabResultItemInput, AddLabResultItemOutput
from app.modules.lab_results.domain.entities import LabResultItem
from app.modules.lab_results.domain.exceptions import (
    InvalidLabOrderItemReferenceError,
    LabResultNotFoundError,
)
from app.modules.lab_results.domain.repositories import LabResultItemRepository, LabResultRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class AddLabResultItem(UseCase[AddLabResultItemInput, AddLabResultItemOutput]):
    def __init__(
        self,
        *,
        lab_result_repository: LabResultRepository,
        lab_result_item_repository: LabResultItemRepository,
        lab_order_query_port: LabOrderQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._lab_results = lab_result_repository
        self._items = lab_result_item_repository
        self._lab_orders = lab_order_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: AddLabResultItemInput) -> AddLabResultItemOutput:
        lab_result = await self._lab_results.get_by_id(input_dto.lab_result_id)
        if lab_result is None:
            raise LabResultNotFoundError(input_dto.lab_result_id)

        lab_result.ensure_editable()

        lab_order_summary = await self._lab_orders.get_lab_order_summary(lab_result.lab_order_id)
        known_item_ids = (
            {item.lab_order_item_id for item in lab_order_summary.items}
            if lab_order_summary is not None
            else set()
        )
        if input_dto.lab_order_item_id not in known_item_ids:
            raise InvalidLabOrderItemReferenceError(
                input_dto.lab_order_item_id, lab_result.lab_order_id
            )

        item = LabResultItem.create(
            lab_result_id=lab_result.id,
            lab_order_item_id=input_dto.lab_order_item_id,
            test_code=input_dto.test_code,
            test_name=input_dto.test_name,
            result_value=input_dto.result_value,
            abnormal_flag=input_dto.abnormal_flag,
            result_unit=input_dto.result_unit,
            reference_range=input_dto.reference_range,
            interpretation=input_dto.interpretation,
        )
        await self._items.add(item)
        self._uow.collect_events(item.pull_events())
        await self._uow.commit()

        return AddLabResultItemOutput(lab_result_item_id=item.id, lab_result_id=lab_result.id)
