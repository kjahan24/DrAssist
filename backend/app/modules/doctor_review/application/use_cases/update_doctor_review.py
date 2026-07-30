"""`UpdateDoctorReview` — "Approved and Rejected records cannot be
edited", enforced solely by `DoctorReview.ensure_editable()` (this
aggregate's own status self-check, called internally by
`update_details()` — raises `DoctorReviewNotEditableError`).

Before applying the update, the *effective* `approved_*` values (input
value if provided, otherwise the review's current value — the same
"unchanged means keep current" semantics `update_details()` itself uses)
are re-validated through `DoctorReviewConsistencyService`, so a review
already `Pending`/`ReturnedForRevision` with `approved_lab_orders=True`
can't be edited into referencing a lab order category that was since
retracted, and a category newly flipped to `True` here is checked the
same way it would be at creation.
"""

from app.modules.doctor_review.application.dto import (
    UpdateDoctorReviewInput,
    UpdateDoctorReviewOutput,
)
from app.modules.doctor_review.application.services.doctor_review_consistency_service import (
    DoctorReviewConsistencyService,
)
from app.modules.doctor_review.domain.exceptions import DoctorReviewNotFoundError
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UpdateDoctorReview(UseCase[UpdateDoctorReviewInput, UpdateDoctorReviewOutput]):
    def __init__(
        self,
        *,
        doctor_review_repository: DoctorReviewRepository,
        consistency_service: DoctorReviewConsistencyService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reviews = doctor_review_repository
        self._consistency = consistency_service
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateDoctorReviewInput) -> UpdateDoctorReviewOutput:
        review = await self._reviews.get_by_id(input_dto.doctor_review_id)
        if review is None:
            raise DoctorReviewNotFoundError(input_dto.doctor_review_id)
        review.ensure_editable()

        def _effective(new_value: bool | None, current_value: bool) -> bool:
            return new_value if new_value is not None else current_value

        await self._consistency.ensure_approved_categories_exist(
            clinical_note_id=review.clinical_note_id,
            approved_soap_note=_effective(input_dto.approved_soap_note, review.approved_soap_note),
            approved_prescription=_effective(
                input_dto.approved_prescription, review.approved_prescription
            ),
            approved_lab_orders=_effective(
                input_dto.approved_lab_orders, review.approved_lab_orders
            ),
            approved_lab_results=_effective(
                input_dto.approved_lab_results, review.approved_lab_results
            ),
            approved_reasoning=_effective(input_dto.approved_reasoning, review.approved_reasoning),
            approved_differential_diagnosis=_effective(
                input_dto.approved_differential_diagnosis,
                review.approved_differential_diagnosis,
            ),
            approved_icd10=_effective(input_dto.approved_icd10, review.approved_icd10),
        )

        review.update_details(
            review_comment=input_dto.review_comment,
            approved_clinical_note=input_dto.approved_clinical_note,
            approved_soap_note=input_dto.approved_soap_note,
            approved_prescription=input_dto.approved_prescription,
            approved_lab_orders=input_dto.approved_lab_orders,
            approved_lab_results=input_dto.approved_lab_results,
            approved_reasoning=input_dto.approved_reasoning,
            approved_differential_diagnosis=input_dto.approved_differential_diagnosis,
            approved_icd10=input_dto.approved_icd10,
        )
        await self._reviews.add(review)
        self._uow.collect_events(review.pull_events())
        await self._uow.commit()

        return UpdateDoctorReviewOutput(
            doctor_review_id=review.id, clinical_note_id=review.clinical_note_id
        )
