"""`FinalizeLabResult` — "A Final Lab Result must contain at least one Lab
Result Item", the one invariant in this module that spans two separate
aggregates (`LabResult` and `LabResultItem`).

Because `LabResultItem` is its own top-level aggregate rather than an
in-memory child of `LabResult` (see `domain/entities.py` for why), this
use case is the *only* place "at least one item" can be checked: it loads
the item list via `LabResultItemRepository.list_by_lab_result` and raises
`LabResultRequiresAtLeastOneItemError` before ever calling
`LabResult.finalize()` — the identical reasoning
`app.modules.prescriptions.application.use_cases.finalize_prescription
.FinalizePrescription` already applies to its own cross-aggregate check.

Gated by `LabResult.ensure_editable()` alone — no `LabOrderQueryPort`
call at all; see `domain/entities.py` for why this module never checks
the parent's editability.
"""

from app.modules.lab_results.application.dto import (
    FinalizeLabResultInput,
    FinalizeLabResultOutput,
)
from app.modules.lab_results.domain.exceptions import (
    LabResultNotFoundError,
    LabResultRequiresAtLeastOneItemError,
)
from app.modules.lab_results.domain.repositories import LabResultItemRepository, LabResultRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class FinalizeLabResult(UseCase[FinalizeLabResultInput, FinalizeLabResultOutput]):
    def __init__(
        self,
        *,
        lab_result_repository: LabResultRepository,
        lab_result_item_repository: LabResultItemRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._lab_results = lab_result_repository
        self._items = lab_result_item_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: FinalizeLabResultInput) -> FinalizeLabResultOutput:
        lab_result = await self._lab_results.get_by_id(input_dto.lab_result_id)
        if lab_result is None:
            raise LabResultNotFoundError(input_dto.lab_result_id)

        items = await self._items.list_by_lab_result(lab_result.id)
        if not items:
            raise LabResultRequiresAtLeastOneItemError(lab_result.id)

        lab_result.finalize()
        await self._lab_results.add(lab_result)
        self._uow.collect_events(lab_result.pull_events())
        await self._uow.commit()

        return FinalizeLabResultOutput(
            lab_result_id=lab_result.id,
            lab_order_id=lab_result.lab_order_id,
            status=lab_result.status,
        )
