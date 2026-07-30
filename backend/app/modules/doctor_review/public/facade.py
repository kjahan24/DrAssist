"""`DoctorReviewFacade` — the one concrete implementation of
`DoctorReviewQueryPort`. Constructed per-request by
`app.modules.doctor_review.container.build_doctor_review_facade`, bound
to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.doctor_review.application.services.doctor_review_query_service import (
    DoctorReviewQueryService,
)
from app.modules.doctor_review.public.dto import DoctorReviewSummaryDTO
from app.modules.doctor_review.public.interfaces import DoctorReviewQueryPort


class DoctorReviewFacade(DoctorReviewQueryPort):
    def __init__(self, *, query_service: DoctorReviewQueryService) -> None:
        self._query_service = query_service

    async def doctor_review_exists(self, doctor_review_id: UUID) -> bool:
        return await self._query_service.doctor_review_exists(doctor_review_id)

    async def is_editable(self, doctor_review_id: UUID) -> bool:
        return await self._query_service.is_editable(doctor_review_id)

    async def get_doctor_review_summary(
        self, doctor_review_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        return await self._query_service.get_doctor_review_summary(doctor_review_id)

    async def get_doctor_review_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        return await self._query_service.get_doctor_review_for_clinical_note(clinical_note_id)

    async def list_doctor_reviews_for_patient(
        self, patient_id: UUID
    ) -> list[DoctorReviewSummaryDTO]:
        return await self._query_service.list_doctor_reviews_for_patient(patient_id)
