"""`UpdateClinicalReasoning` — "Approved/Rejected reasoning becomes
immutable", enforced solely by `ClinicalReasoning.ensure_editable()` (this
aggregate's own status self-check, called internally by
`update_details()` — raises `ClinicalReasoningNotEditableError`). No
cross-module port call here — see `domain/entities.py` for why this
module never checks `ClinicalNoteQueryPort.is_editable`. Only
`reasoning_text`/`confidence_score` are mutable; `reasoning_source`/
`ai_generated` and every identity field are immutable once set — see
`domain/entities.py`.
"""

from app.modules.clinical_reasoning.application.dto import (
    UpdateClinicalReasoningInput,
    UpdateClinicalReasoningOutput,
)
from app.modules.clinical_reasoning.domain.exceptions import ClinicalReasoningNotFoundError
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateClinicalReasoning(UseCase[UpdateClinicalReasoningInput, UpdateClinicalReasoningOutput]):
    def __init__(
        self,
        *,
        clinical_reasoning_repository: ClinicalReasoningRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reasoning_records = clinical_reasoning_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: UpdateClinicalReasoningInput
    ) -> UpdateClinicalReasoningOutput:
        reasoning = await self._reasoning_records.get_by_id(input_dto.clinical_reasoning_id)
        if reasoning is None:
            raise ClinicalReasoningNotFoundError(input_dto.clinical_reasoning_id)

        reasoning.update_details(
            reasoning_text=input_dto.reasoning_text,
            confidence_score=input_dto.confidence_score,
        )
        await self._reasoning_records.add(reasoning)
        self._uow.collect_events(reasoning.pull_events())
        await self._uow.commit()

        return UpdateClinicalReasoningOutput(
            clinical_reasoning_id=reasoning.id, clinical_note_id=reasoning.clinical_note_id
        )
