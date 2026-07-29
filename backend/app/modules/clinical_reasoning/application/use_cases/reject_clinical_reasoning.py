"""`RejectClinicalReasoning` ((Pending|Reviewed) -> Rejected) — the
mirror of `ApproveClinicalReasoning`; see that use case's own docstring
for why it is allowed from either non-terminal state and also sets
`reviewed_by_doctor = True`.
"""

from app.modules.clinical_reasoning.application.dto import (
    ClinicalReasoningReviewStatusOutput,
    RejectClinicalReasoningInput,
)
from app.modules.clinical_reasoning.domain.exceptions import ClinicalReasoningNotFoundError
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RejectClinicalReasoning(
    UseCase[RejectClinicalReasoningInput, ClinicalReasoningReviewStatusOutput]
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
        self, input_dto: RejectClinicalReasoningInput
    ) -> ClinicalReasoningReviewStatusOutput:
        reasoning = await self._reasoning_records.get_by_id(input_dto.clinical_reasoning_id)
        if reasoning is None:
            raise ClinicalReasoningNotFoundError(input_dto.clinical_reasoning_id)

        reasoning.reject()
        await self._reasoning_records.add(reasoning)
        self._uow.collect_events(reasoning.pull_events())
        await self._uow.commit()

        return ClinicalReasoningReviewStatusOutput(
            clinical_reasoning_id=reasoning.id,
            clinical_note_id=reasoning.clinical_note_id,
            review_status=reasoning.review_status,
        )
