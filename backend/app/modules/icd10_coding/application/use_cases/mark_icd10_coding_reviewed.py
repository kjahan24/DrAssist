"""`MarkICD10CodingReviewed` (Pending -> Reviewed) — the narrow transition
a doctor takes to acknowledge having looked at an AI/Hybrid-generated
code before deciding to `approve()`/`reject()` it. Requires
`review_status` to currently be `Pending` (`ICD10Coding.mark_reviewed()`
raises `ReviewRequiresPendingStatusError` otherwise) — physician-
generated codes start at `Reviewed` already (see `domain/entities.py`),
so this transition is only ever exercised for AI/Hybrid-generated codes.
"""

from app.modules.icd10_coding.application.dto import (
    ICD10CodingReviewStatusOutput,
    MarkICD10CodingReviewedInput,
)
from app.modules.icd10_coding.domain.exceptions import ICD10CodingNotFoundError
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class MarkICD10CodingReviewed(UseCase[MarkICD10CodingReviewedInput, ICD10CodingReviewStatusOutput]):
    def __init__(
        self, *, icd10_coding_repository: ICD10CodingRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._codings = icd10_coding_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: MarkICD10CodingReviewedInput
    ) -> ICD10CodingReviewStatusOutput:
        coding = await self._codings.get_by_id(input_dto.icd10_coding_id)
        if coding is None:
            raise ICD10CodingNotFoundError(input_dto.icd10_coding_id)

        coding.mark_reviewed()
        await self._codings.add(coding)
        self._uow.collect_events(coding.pull_events())
        await self._uow.commit()

        return ICD10CodingReviewStatusOutput(
            icd10_coding_id=coding.id,
            clinical_note_id=coding.clinical_note_id,
            review_status=coding.review_status,
        )
