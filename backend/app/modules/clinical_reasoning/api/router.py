"""HTTP routes for the Clinical Reasoning module.

Follows the pattern established in `app.modules.lab_orders.api.router`:
`ClinicalReasoning` is one-to-many with `ClinicalNote`, so `GET` is keyed
by the reasoning record's own id, with separate list-by-clinical-note and
list-by-patient collection endpoints. `mark-reviewed`/`approve`/`reject`
are the review-workflow status transitions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.clinical_reasoning.api.dependencies import (
    get_approve_clinical_reasoning_use_case,
    get_clinical_reasoning_query_service,
    get_create_clinical_reasoning_use_case,
    get_mark_clinical_reasoning_reviewed_use_case,
    get_reject_clinical_reasoning_use_case,
    get_update_clinical_reasoning_use_case,
)
from app.modules.clinical_reasoning.api.schemas import (
    ClinicalReasoningResponse,
    CreateClinicalReasoningRequest,
    UpdateClinicalReasoningRequest,
)
from app.modules.clinical_reasoning.application.dto import (
    ApproveClinicalReasoningInput,
    CreateClinicalReasoningInput,
    MarkClinicalReasoningReviewedInput,
    RejectClinicalReasoningInput,
    UpdateClinicalReasoningInput,
)
from app.modules.clinical_reasoning.application.services.clinical_reasoning_query_service import (
    ClinicalReasoningQueryService,
)
from app.modules.clinical_reasoning.application.use_cases.approve_clinical_reasoning import (
    ApproveClinicalReasoning,
)
from app.modules.clinical_reasoning.application.use_cases.create_clinical_reasoning import (
    CreateClinicalReasoning,
)
from app.modules.clinical_reasoning.application.use_cases.mark_clinical_reasoning_reviewed import (
    MarkClinicalReasoningReviewed,
)
from app.modules.clinical_reasoning.application.use_cases.reject_clinical_reasoning import (
    RejectClinicalReasoning,
)
from app.modules.clinical_reasoning.application.use_cases.update_clinical_reasoning import (
    UpdateClinicalReasoning,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"reasoning_source", "review_status", "ai_generated"})

QueryService = Annotated[
    ClinicalReasoningQueryService, Depends(get_clinical_reasoning_query_service)
]
CreateUseCase = Annotated[CreateClinicalReasoning, Depends(get_create_clinical_reasoning_use_case)]
UpdateUseCase = Annotated[UpdateClinicalReasoning, Depends(get_update_clinical_reasoning_use_case)]
MarkReviewedUseCase = Annotated[
    MarkClinicalReasoningReviewed, Depends(get_mark_clinical_reasoning_reviewed_use_case)
]
ApproveUseCase = Annotated[
    ApproveClinicalReasoning, Depends(get_approve_clinical_reasoning_use_case)
]
RejectUseCase = Annotated[RejectClinicalReasoning, Depends(get_reject_clinical_reasoning_use_case)]


async def _get_response(
    clinical_reasoning_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> ClinicalReasoningResponse:
    summary = await query_service.get_clinical_reasoning_summary(clinical_reasoning_id)
    if summary is None:
        raise NotFoundError(f"no clinical reasoning found with id {clinical_reasoning_id}")
    response = ClinicalReasoningResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("", response_model=ClinicalReasoningResponse, status_code=status.HTTP_201_CREATED)
async def create_clinical_reasoning(
    body: CreateClinicalReasoningRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ClinicalReasoningResponse:
    output = await use_case.execute(
        CreateClinicalReasoningInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response(output.clinical_reasoning_id, query_service, current_user)


@router.get("/{clinical_reasoning_id}", response_model=ClinicalReasoningResponse)
async def get_clinical_reasoning(
    clinical_reasoning_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> ClinicalReasoningResponse:
    return await _get_response(clinical_reasoning_id, query_service, current_user)


@router.get(
    "/clinical-note/{clinical_note_id}",
    response_model=PaginatedResponse[ClinicalReasoningResponse],
)
async def list_clinical_reasoning_for_clinical_note(
    clinical_note_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[ClinicalReasoningResponse]:
    summaries = await query_service.list_clinical_reasoning_for_clinical_note(clinical_note_id)
    items = [ClinicalReasoningResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[ClinicalReasoningResponse])
async def list_clinical_reasoning_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[ClinicalReasoningResponse]:
    summaries = await query_service.list_clinical_reasoning_for_patient(patient_id)
    items = [ClinicalReasoningResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.put("/{clinical_reasoning_id}", response_model=ClinicalReasoningResponse)
async def update_clinical_reasoning(
    clinical_reasoning_id: UUID,
    body: UpdateClinicalReasoningRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ClinicalReasoningResponse:
    await use_case.execute(
        UpdateClinicalReasoningInput(
            clinical_reasoning_id=clinical_reasoning_id, **body.model_dump()
        )
    )
    return await _get_response(clinical_reasoning_id, query_service, current_user)


@router.patch("/{clinical_reasoning_id}/mark-reviewed", response_model=ClinicalReasoningResponse)
async def mark_clinical_reasoning_reviewed(
    clinical_reasoning_id: UUID,
    use_case: MarkReviewedUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ClinicalReasoningResponse:
    await use_case.execute(
        MarkClinicalReasoningReviewedInput(clinical_reasoning_id=clinical_reasoning_id)
    )
    return await _get_response(clinical_reasoning_id, query_service, current_user)


@router.patch("/{clinical_reasoning_id}/approve", response_model=ClinicalReasoningResponse)
async def approve_clinical_reasoning(
    clinical_reasoning_id: UUID,
    use_case: ApproveUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ClinicalReasoningResponse:
    await use_case.execute(
        ApproveClinicalReasoningInput(clinical_reasoning_id=clinical_reasoning_id)
    )
    return await _get_response(clinical_reasoning_id, query_service, current_user)


@router.patch("/{clinical_reasoning_id}/reject", response_model=ClinicalReasoningResponse)
async def reject_clinical_reasoning(
    clinical_reasoning_id: UUID,
    use_case: RejectUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ClinicalReasoningResponse:
    await use_case.execute(
        RejectClinicalReasoningInput(clinical_reasoning_id=clinical_reasoning_id)
    )
    return await _get_response(clinical_reasoning_id, query_service, current_user)
