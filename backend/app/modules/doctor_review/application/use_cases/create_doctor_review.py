"""`CreateDoctorReview` — a doctor review always references exactly one
existing `ClinicalNote`, and a clinical note may have *at most one*
doctor review ("One Clinical Note has exactly zero or one Doctor
Review"), the same one-to-one shape
`app.modules.soap_notes.application.use_cases.create_soap_note
.CreateSOAPNote` already establishes, just with an explicit duplicate
check up front rather than relying solely on the database's unique
index (`DuplicateDoctorReviewError`, the same "query first, then
construct" technique used throughout this codebase's uniqueness rules).

Resolves the parent through `ClinicalNoteQueryPort` and derives all four
identity fields — `organization_id`, `patient_id`, `visit_id`,
`doctor_id` — from that single lookup, which is what makes "Patient,
Visit, Organization, and Doctor must match the linked Clinical Note"
true unconditionally. A missing clinical note raises
`ClinicalNoteNotFoundError` (defined locally — see `domain/exceptions.py`
for why).

"Cross-module consistency" for the `approved_*` checklist is delegated
to `DoctorReviewConsistencyService` — see that service's own docstring.
"""

from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.doctor_review.application.dto import (
    CreateDoctorReviewInput,
    CreateDoctorReviewOutput,
)
from app.modules.doctor_review.application.services.doctor_review_consistency_service import (
    DoctorReviewConsistencyService,
)
from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.exceptions import (
    ClinicalNoteNotFoundError,
    DuplicateDoctorReviewError,
)
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateDoctorReview(UseCase[CreateDoctorReviewInput, CreateDoctorReviewOutput]):
    def __init__(
        self,
        *,
        doctor_review_repository: DoctorReviewRepository,
        clinical_note_query_port: ClinicalNoteQueryPort,
        consistency_service: DoctorReviewConsistencyService,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reviews = doctor_review_repository
        self._clinical_notes = clinical_note_query_port
        self._consistency = consistency_service
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateDoctorReviewInput) -> CreateDoctorReviewOutput:
        clinical_note_summary = await self._clinical_notes.get_clinical_note_summary(
            input_dto.clinical_note_id
        )
        if clinical_note_summary is None:
            raise ClinicalNoteNotFoundError(input_dto.clinical_note_id)

        existing = await self._reviews.get_by_clinical_note_id(input_dto.clinical_note_id)
        if existing is not None:
            raise DuplicateDoctorReviewError(input_dto.clinical_note_id)

        await self._consistency.ensure_approved_categories_exist(
            clinical_note_id=input_dto.clinical_note_id,
            approved_soap_note=input_dto.approved_soap_note,
            approved_prescription=input_dto.approved_prescription,
            approved_lab_orders=input_dto.approved_lab_orders,
            approved_lab_results=input_dto.approved_lab_results,
            approved_reasoning=input_dto.approved_reasoning,
            approved_differential_diagnosis=input_dto.approved_differential_diagnosis,
            approved_icd10=input_dto.approved_icd10,
        )

        review = DoctorReview.create(
            organization_id=clinical_note_summary.organization_id,
            patient_id=clinical_note_summary.patient_id,
            visit_id=clinical_note_summary.visit_id,
            doctor_id=clinical_note_summary.doctor_id,
            clinical_note_id=input_dto.clinical_note_id,
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

        return CreateDoctorReviewOutput(
            doctor_review_id=review.id,
            organization_id=review.organization_id,
            clinical_note_id=review.clinical_note_id,
            review_status=review.review_status,
        )
