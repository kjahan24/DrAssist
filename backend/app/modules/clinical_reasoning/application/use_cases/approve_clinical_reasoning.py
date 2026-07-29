"""`ApproveClinicalReasoning` ((Pending|Reviewed) -> Approved) — allowed
from either non-terminal state (`ClinicalReasoning.ensure_editable()`),
not only after an explicit `mark_reviewed()` step: nothing in this task's
business rules requires passing through `Reviewed` first, only that
`Approved`/`Rejected` become immutable once reached. Also sets
`reviewed_by_doctor = True` as part of approving — an approved record
with no reviewer would be an internal contradiction; see
`domain/entities.py`.
"""

from app.modules.clinical_reasoning.application.dto import (
    ApproveClinicalReasoningInput,
    ClinicalReasoningReviewStatusOutput,
)
from app.modules.clinical_reasoning.domain.exceptions import ClinicalReasoningNotFoundError
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ApproveClinicalReasoning(
    UseCase[ApproveClinicalReasoningInput, ClinicalReasoningReviewStatusOutput]
):
    def __init__(
        self,
        *,
        clinical_reasoning_repository: ClinicalReasoningRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reasoning_records = clinical_reasoning_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: ApproveClinicalReasoningInput
    ) -> ClinicalReasoningReviewStatusOutput:
        reasoning = await self._reasoning_records.get_by_id(input_dto.clinical_reasoning_id)
        if reasoning is None:
            raise ClinicalReasoningNotFoundError(input_dto.clinical_reasoning_id)

        reasoning.approve()
        await self._reasoning_records.add(reasoning)
        self._uow.collect_events(reasoning.pull_events())
        await self._uow.commit()

        return ClinicalReasoningReviewStatusOutput(
            clinical_reasoning_id=reasoning.id,
            clinical_note_id=reasoning.clinical_note_id,
            review_status=reasoning.review_status,
        )
