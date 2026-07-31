"""HTTP routes for the Doctor Review module.

`DoctorReview` is one-to-zero-or-one with `ClinicalNote`, so `GET` uses
`/doctor-reviews/clinical-note/{clinical_note_id}` as the primary lookup
(matching `app.modules.soap_notes.api.router`'s own 1:1 shape), plus a
by-own-id `GET` since this aggregate has an independent status lifecycle
consumers may reference directly — see
`DoctorReviewQueryService`'s own docstring. Status transitions:
`approve`/`reject`/`return-for-revision`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.doctor_review.api.dependencies import (
    get_approve_doctor_review_use_case,
    get_create_doctor_review_use_case,
    get_doctor_review_query_service,
    get_reject_doctor_review_use_case,
    get_return_doctor_review_for_revision_use_case,
    get_update_doctor_review_use_case,
)
from app.modules.doctor_review.api.schemas import (
    CreateDoctorReviewRequest,
    DoctorReviewResponse,
    UpdateDoctorReviewRequest,
)
from app.modules.doctor_review.application.dto import (
    ApproveDoctorReviewInput,
    CreateDoctorReviewInput,
    RejectDoctorReviewInput,
    ReturnDoctorReviewForRevisionInput,
    UpdateDoctorReviewInput,
)
from app.modules.doctor_review.application.services.doctor_review_query_service import (
    DoctorReviewQueryService,
)
from app.modules.doctor_review.application.use_cases.approve_doctor_review import (
    ApproveDoctorReview,
)
from app.modules.doctor_review.application.use_cases.create_doctor_review import (
    CreateDoctorReview,
)
from app.modules.doctor_review.application.use_cases.reject_doctor_review import (
    RejectDoctorReview,
)
from app.modules.doctor_review.application.use_cases.return_doctor_review_for_revision import (
    ReturnDoctorReviewForRevision,
)
from app.modules.doctor_review.application.use_cases.update_doctor_review import (
    UpdateDoctorReview,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

QueryService = Annotated[DoctorReviewQueryService, Depends(get_doctor_review_query_service)]
CreateUseCase = Annotated[CreateDoctorReview, Depends(get_create_doctor_review_use_case)]
UpdateUseCase = Annotated[UpdateDoctorReview, Depends(get_update_doctor_review_use_case)]
ApproveUseCase = Annotated[ApproveDoctorReview, Depends(get_approve_doctor_review_use_case)]
RejectUseCase = Annotated[RejectDoctorReview, Depends(get_reject_doctor_review_use_case)]
ReturnForRevisionUseCase = Annotated[
    ReturnDoctorReviewForRevision, Depends(get_return_doctor_review_for_revision_use_case)
]


async def _get_response(
    doctor_review_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> DoctorReviewResponse:
    summary = await query_service.get_doctor_review_summary(doctor_review_id)
    if summary is None:
        raise NotFoundError(f"no doctor review found with id {doctor_review_id}")
    response = DoctorReviewResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("", response_model=DoctorReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor_review(
    body: CreateDoctorReviewRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DoctorReviewResponse:
    output = await use_case.execute(
        CreateDoctorReviewInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response(output.doctor_review_id, query_service, current_user)


@router.get("/{doctor_review_id}", response_model=DoctorReviewResponse)
async def get_doctor_review(
    doctor_review_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> DoctorReviewResponse:
    return await _get_response(doctor_review_id, query_service, current_user)


@router.get("/clinical-note/{clinical_note_id}", response_model=DoctorReviewResponse)
async def get_doctor_review_for_clinical_note(
    clinical_note_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> DoctorReviewResponse:
    summary = await query_service.get_doctor_review_for_clinical_note(clinical_note_id)
    if summary is None:
        raise NotFoundError(f"no doctor review found for clinical note {clinical_note_id}")
    response = DoctorReviewResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[DoctorReviewResponse])
async def list_doctor_reviews_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DoctorReviewResponse]:
    summaries = await query_service.list_doctor_reviews_for_patient(patient_id)
    items = [DoctorReviewResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"review_status", "reviewed_at"}),
    )


@router.put("/{doctor_review_id}", response_model=DoctorReviewResponse)
async def update_doctor_review(
    doctor_review_id: UUID,
    body: UpdateDoctorReviewRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DoctorReviewResponse:
    await use_case.execute(
        UpdateDoctorReviewInput(doctor_review_id=doctor_review_id, **body.model_dump())
    )
    return await _get_response(doctor_review_id, query_service, current_user)


@router.patch("/{doctor_review_id}/approve", response_model=DoctorReviewResponse)
async def approve_doctor_review(
    doctor_review_id: UUID,
    use_case: ApproveUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DoctorReviewResponse:
    await use_case.execute(ApproveDoctorReviewInput(doctor_review_id=doctor_review_id))
    return await _get_response(doctor_review_id, query_service, current_user)


@router.patch("/{doctor_review_id}/reject", response_model=DoctorReviewResponse)
async def reject_doctor_review(
    doctor_review_id: UUID,
    use_case: RejectUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DoctorReviewResponse:
    await use_case.execute(RejectDoctorReviewInput(doctor_review_id=doctor_review_id))
    return await _get_response(doctor_review_id, query_service, current_user)


@router.patch("/{doctor_review_id}/return-for-revision", response_model=DoctorReviewResponse)
async def return_doctor_review_for_revision(
    doctor_review_id: UUID,
    use_case: ReturnForRevisionUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DoctorReviewResponse:
    await use_case.execute(ReturnDoctorReviewForRevisionInput(doctor_review_id=doctor_review_id))
    return await _get_response(doctor_review_id, query_service, current_user)
