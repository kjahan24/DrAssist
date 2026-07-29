"""`UpdateLabResult` — "Final Lab Results become read-only", enforced
solely by `LabResult.ensure_editable()` (this aggregate's own Draft-only
self-check, called internally by `update_details()` — raises
`LabResultNotEditableError`). No cross-module port call here — see
`domain/entities.py` for why this module never checks
`LabOrderQueryPort.is_editable`. Only `laboratory_name`/`comments` are
mutable; `result_number`/`reported_at` and every identity field are
immutable once set — see `domain/entities.py`.
"""

from app.modules.lab_results.application.dto import UpdateLabResultInput, UpdateLabResultOutput
from app.modules.lab_results.domain.exceptions import LabResultNotFoundError
from app.modules.lab_results.domain.repositories import LabResultRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateLabResult(UseCase[UpdateLabResultInput, UpdateLabResultOutput]):
    def __init__(
        self, *, lab_result_repository: LabResultRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._lab_results = lab_result_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateLabResultInput) -> UpdateLabResultOutput:
        lab_result = await self._lab_results.get_by_id(input_dto.lab_result_id)
        if lab_result is None:
            raise LabResultNotFoundError(input_dto.lab_result_id)

        lab_result.update_details(
            laboratory_name=input_dto.laboratory_name, comments=input_dto.comments
        )
        await self._lab_results.add(lab_result)
        self._uow.collect_events(lab_result.pull_events())
        await self._uow.commit()

        return UpdateLabResultOutput(
            lab_result_id=lab_result.id, lab_order_id=lab_result.lab_order_id
        )
