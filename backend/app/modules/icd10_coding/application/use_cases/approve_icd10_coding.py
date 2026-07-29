"""`ApproveICD10Coding` ((Pending|Reviewed) -> Approved) — allowed from
either non-terminal state (`ICD10Coding.ensure_editable()`), not only
after an explicit `mark_reviewed()` step: nothing in this task's business
rules requires passing through `Reviewed` first, only that `Approved`/
`Rejected` become read-only once reached.
"""

from app.modules.icd10_coding.application.dto import (
    ApproveICD10CodingInput,
    ICD10CodingReviewStatusOutput,
)
from app.modules.icd10_coding.domain.exceptions import ICD10CodingNotFoundError
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ApproveICD10Coding(UseCase[ApproveICD10CodingInput, ICD10CodingReviewStatusOutput]):
    def __init__(
        self, *, icd10_coding_repository: ICD10CodingRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._codings = icd10_coding_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: ApproveICD10CodingInput) -> ICD10CodingReviewStatusOutput:
        coding = await self._codings.get_by_id(input_dto.icd10_coding_id)
        if coding is None:
            raise ICD10CodingNotFoundError(input_dto.icd10_coding_id)

        coding.approve()
        await self._codings.add(coding)
        self._uow.collect_events(coding.pull_events())
        await self._uow.commit()

        return ICD10CodingReviewStatusOutput(
            icd10_coding_id=coding.id,
            clinical_note_id=coding.clinical_note_id,
            review_status=coding.review_status,
        )
