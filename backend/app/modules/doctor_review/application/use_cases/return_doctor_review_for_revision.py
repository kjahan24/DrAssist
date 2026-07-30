"""`ReturnDoctorReviewForRevision` (Pending -> ReturnedForRevision) —
"ReturnedForRevision keeps the record editable". Only allowed from
`Pending` (`DoctorReview._transition_to()`'s own transition map) —
`ReturnedForRevision` itself only transitions onward to `Approved`/
`Rejected`, since this task's Business Rules describe no resubmission
cycle; see `domain/entities.py` for the full reasoning.
"""

from app.modules.doctor_review.application.dto import (
    DoctorReviewStatusOutput,
    ReturnDoctorReviewForRevisionInput,
)
from app.modules.doctor_review.domain.exceptions import DoctorReviewNotFoundError
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class ReturnDoctorReviewForRevision(
    UseCase[ReturnDoctorReviewForRevisionInput, DoctorReviewStatusOutput]
):
    def __init__(
        self, *, doctor_review_repository: DoctorReviewRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._reviews = doctor_review_repository
        self._uow = unit_of_work

    async def execute(
        self, input_dto: ReturnDoctorReviewForRevisionInput
    ) -> DoctorReviewStatusOutput:
        review = await self._reviews.get_by_id(input_dto.doctor_review_id)
        if review is None:
            raise DoctorReviewNotFoundError(input_dto.doctor_review_id)

        review.return_for_revision()
        await self._reviews.add(review)
        self._uow.collect_events(review.pull_events())
        await self._uow.commit()

        return DoctorReviewStatusOutput(
            doctor_review_id=review.id,
            clinical_note_id=review.clinical_note_id,
            review_status=review.review_status,
            reviewed_at=review.reviewed_at,
        )
