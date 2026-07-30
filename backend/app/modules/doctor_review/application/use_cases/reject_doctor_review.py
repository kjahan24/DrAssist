"""`RejectDoctorReview` ((Pending|ReturnedForRevision) -> Rejected) —
"Rejected also becomes immutable". The mirror of `ApproveDoctorReview`;
see that use case's own docstring.
"""

from app.modules.doctor_review.application.dto import (
    DoctorReviewStatusOutput,
    RejectDoctorReviewInput,
)
from app.modules.doctor_review.domain.exceptions import DoctorReviewNotFoundError
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class RejectDoctorReview(UseCase[RejectDoctorReviewInput, DoctorReviewStatusOutput]):
    def __init__(
        self, *, doctor_review_repository: DoctorReviewRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._reviews = doctor_review_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: RejectDoctorReviewInput) -> DoctorReviewStatusOutput:
        review = await self._reviews.get_by_id(input_dto.doctor_review_id)
        if review is None:
            raise DoctorReviewNotFoundError(input_dto.doctor_review_id)

        review.reject()
        await self._reviews.add(review)
        self._uow.collect_events(review.pull_events())
        await self._uow.commit()

        return DoctorReviewStatusOutput(
            doctor_review_id=review.id,
            clinical_note_id=review.clinical_note_id,
            review_status=review.review_status,
            reviewed_at=review.reviewed_at,
        )
