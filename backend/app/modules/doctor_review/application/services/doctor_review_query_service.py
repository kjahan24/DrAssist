"""Read-only queries against `DoctorReview`.

Backs the module's public `DoctorReviewQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`DoctorReview` is one-to-*zero-or-one* with `ClinicalNote` ("One Clinical
Note has exactly zero or one Doctor Review"), so
`get_doctor_review_for_clinical_note` — not a list — is the query keyed
by the parent, the same shape
`app.modules.soap_notes.application.services.soap_note_query_service
.SOAPNoteQueryService` uses for its own one-to-one place.
`get_doctor_review_summary`/`is_editable` are instead keyed by this
aggregate's own id — kept (unlike `SOAPNote`, which exposes no id-keyed
access at all) because this aggregate owns an independent status
lifecycle a future consumer (Electronic Signature, Multi-stage Approval,
Clinical Audit) needs to reference directly by `doctor_review_id`, not
only by way of its clinical note — see `container.py`'s scope note.
`list_doctor_reviews_for_patient` exists for the same reason
`app.modules.clinical_notes.application.services
.clinical_note_query_service.ClinicalNoteQueryService
.list_clinical_notes_for_patient` does: a future Clinical Audit/Hospital
Review Committee module can assemble a patient's full review history
without this module needing to change.
"""

from uuid import UUID

from app.modules.doctor_review.application.dto import DoctorReviewSummaryDTO
from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.enums import ReviewStatus
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository

_NOT_EDITABLE_STATUSES = frozenset({ReviewStatus.APPROVED, ReviewStatus.REJECTED})


class DoctorReviewQueryService:
    def __init__(self, *, doctor_review_repository: DoctorReviewRepository) -> None:
        self._reviews = doctor_review_repository

    async def doctor_review_exists(self, doctor_review_id: UUID) -> bool:
        return await self._reviews.get_by_id(doctor_review_id) is not None

    async def is_editable(self, doctor_review_id: UUID) -> bool:
        review = await self._reviews.get_by_id(doctor_review_id)
        return review is not None and review.review_status not in _NOT_EDITABLE_STATUSES

    async def get_doctor_review_summary(
        self, doctor_review_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        review = await self._reviews.get_by_id(doctor_review_id)
        return _to_summary(review) if review is not None else None

    async def get_doctor_review_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> DoctorReviewSummaryDTO | None:
        review = await self._reviews.get_by_clinical_note_id(clinical_note_id)
        return _to_summary(review) if review is not None else None

    async def list_doctor_reviews_for_patient(
        self, patient_id: UUID
    ) -> list[DoctorReviewSummaryDTO]:
        reviews = await self._reviews.list_by_patient(patient_id)
        return [_to_summary(review) for review in reviews]


def _to_summary(review: DoctorReview) -> DoctorReviewSummaryDTO:
    return DoctorReviewSummaryDTO(
        doctor_review_id=review.id,
        organization_id=review.organization_id,
        patient_id=review.patient_id,
        visit_id=review.visit_id,
        doctor_id=review.doctor_id,
        clinical_note_id=review.clinical_note_id,
        review_status=review.review_status,
        review_comment=review.review_comment,
        reviewed_at=review.reviewed_at,
        approved_clinical_note=review.approved_clinical_note,
        approved_soap_note=review.approved_soap_note,
        approved_prescription=review.approved_prescription,
        approved_lab_orders=review.approved_lab_orders,
        approved_lab_results=review.approved_lab_results,
        approved_reasoning=review.approved_reasoning,
        approved_differential_diagnosis=review.approved_differential_diagnosis,
        approved_icd10=review.approved_icd10,
    )
