"""HTTP routes for the ICD-10 Coding module.

Follows the pattern established in
`app.modules.differential_diagnosis.api.router` — same one-to-many-with-
`ClinicalNote` shape and review-workflow transitions, plus
`mark-primary`/`unmark-primary` and a `GET .../primary` lookup unique to
this module.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.icd10_coding.api.dependencies import (
    get_approve_icd10_coding_use_case,
    get_create_icd10_coding_use_case,
    get_icd10_coding_query_service,
    get_mark_icd10_coding_as_primary_use_case,
    get_mark_icd10_coding_reviewed_use_case,
    get_reject_icd10_coding_use_case,
    get_unmark_icd10_coding_as_primary_use_case,
    get_update_icd10_coding_use_case,
)
from app.modules.icd10_coding.api.schemas import (
    CreateICD10CodingRequest,
    ICD10CodingResponse,
    UpdateICD10CodingRequest,
)
from app.modules.icd10_coding.application.dto import (
    ApproveICD10CodingInput,
    CreateICD10CodingInput,
    MarkICD10CodingAsPrimaryInput,
    MarkICD10CodingReviewedInput,
    RejectICD10CodingInput,
    UnmarkICD10CodingAsPrimaryInput,
    UpdateICD10CodingInput,
)
from app.modules.icd10_coding.application.services.icd10_coding_query_service import (
    ICD10CodingQueryService,
)
from app.modules.icd10_coding.application.use_cases.approve_icd10_coding import (
    ApproveICD10Coding,
)
from app.modules.icd10_coding.application.use_cases.create_icd10_coding import CreateICD10Coding
from app.modules.icd10_coding.application.use_cases.mark_icd10_coding_as_primary import (
    MarkICD10CodingAsPrimary,
)
from app.modules.icd10_coding.application.use_cases.mark_icd10_coding_reviewed import (
    MarkICD10CodingReviewed,
)
from app.modules.icd10_coding.application.use_cases.reject_icd10_coding import RejectICD10Coding
from app.modules.icd10_coding.application.use_cases.unmark_icd10_coding_as_primary import (
    UnmarkICD10CodingAsPrimary,
)
from app.modules.icd10_coding.application.use_cases.update_icd10_coding import UpdateICD10Coding
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"icd10_code", "coding_source", "review_status", "primary_code"})

QueryService = Annotated[ICD10CodingQueryService, Depends(get_icd10_coding_query_service)]
CreateUseCase = Annotated[CreateICD10Coding, Depends(get_create_icd10_coding_use_case)]
UpdateUseCase = Annotated[UpdateICD10Coding, Depends(get_update_icd10_coding_use_case)]
MarkPrimaryUseCase = Annotated[
    MarkICD10CodingAsPrimary, Depends(get_mark_icd10_coding_as_primary_use_case)
]
UnmarkPrimaryUseCase = Annotated[
    UnmarkICD10CodingAsPrimary, Depends(get_unmark_icd10_coding_as_primary_use_case)
]
MarkReviewedUseCase = Annotated[
    MarkICD10CodingReviewed, Depends(get_mark_icd10_coding_reviewed_use_case)
]
ApproveUseCase = Annotated[ApproveICD10Coding, Depends(get_approve_icd10_coding_use_case)]
RejectUseCase = Annotated[RejectICD10Coding, Depends(get_reject_icd10_coding_use_case)]


async def _get_response(
    icd10_coding_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> ICD10CodingResponse:
    summary = await query_service.get_icd10_coding_summary(icd10_coding_id)
    if summary is None:
        raise NotFoundError(f"no ICD-10 coding found with id {icd10_coding_id}")
    response = ICD10CodingResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("", response_model=ICD10CodingResponse, status_code=status.HTTP_201_CREATED)
async def create_icd10_coding(
    body: CreateICD10CodingRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ICD10CodingResponse:
    output = await use_case.execute(
        CreateICD10CodingInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response(output.icd10_coding_id, query_service, current_user)


@router.get("/{icd10_coding_id}", response_model=ICD10CodingResponse)
async def get_icd10_coding(
    icd10_coding_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> ICD10CodingResponse:
    return await _get_response(icd10_coding_id, query_service, current_user)


@router.get("/clinical-note/{clinical_note_id}/primary", response_model=ICD10CodingResponse)
async def get_primary_icd10_coding(
    clinical_note_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> ICD10CodingResponse:
    summary = await query_service.get_primary_icd10_coding_for_clinical_note(clinical_note_id)
    if summary is None:
        raise NotFoundError(f"no primary ICD-10 coding found for clinical note {clinical_note_id}")
    response = ICD10CodingResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get(
    "/clinical-note/{clinical_note_id}", response_model=PaginatedResponse[ICD10CodingResponse]
)
async def list_icd10_codings_for_clinical_note(
    clinical_note_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[ICD10CodingResponse]:
    summaries = await query_service.list_icd10_codings_for_clinical_note(clinical_note_id)
    items = [ICD10CodingResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[ICD10CodingResponse])
async def list_icd10_codings_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[ICD10CodingResponse]:
    summaries = await query_service.list_icd10_codings_for_patient(patient_id)
    items = [ICD10CodingResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.put("/{icd10_coding_id}", response_model=ICD10CodingResponse)
async def update_icd10_coding(
    icd10_coding_id: UUID,
    body: UpdateICD10CodingRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ICD10CodingResponse:
    await use_case.execute(
        UpdateICD10CodingInput(icd10_coding_id=icd10_coding_id, **body.model_dump())
    )
    return await _get_response(icd10_coding_id, query_service, current_user)


@router.patch("/{icd10_coding_id}/mark-primary", response_model=ICD10CodingResponse)
async def mark_icd10_coding_as_primary(
    icd10_coding_id: UUID,
    use_case: MarkPrimaryUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ICD10CodingResponse:
    await use_case.execute(MarkICD10CodingAsPrimaryInput(icd10_coding_id=icd10_coding_id))
    return await _get_response(icd10_coding_id, query_service, current_user)


@router.patch("/{icd10_coding_id}/unmark-primary", response_model=ICD10CodingResponse)
async def unmark_icd10_coding_as_primary(
    icd10_coding_id: UUID,
    use_case: UnmarkPrimaryUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ICD10CodingResponse:
    await use_case.execute(UnmarkICD10CodingAsPrimaryInput(icd10_coding_id=icd10_coding_id))
    return await _get_response(icd10_coding_id, query_service, current_user)


@router.patch("/{icd10_coding_id}/mark-reviewed", response_model=ICD10CodingResponse)
async def mark_icd10_coding_reviewed(
    icd10_coding_id: UUID,
    use_case: MarkReviewedUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ICD10CodingResponse:
    await use_case.execute(MarkICD10CodingReviewedInput(icd10_coding_id=icd10_coding_id))
    return await _get_response(icd10_coding_id, query_service, current_user)


@router.patch("/{icd10_coding_id}/approve", response_model=ICD10CodingResponse)
async def approve_icd10_coding(
    icd10_coding_id: UUID,
    use_case: ApproveUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ICD10CodingResponse:
    await use_case.execute(ApproveICD10CodingInput(icd10_coding_id=icd10_coding_id))
    return await _get_response(icd10_coding_id, query_service, current_user)


@router.patch("/{icd10_coding_id}/reject", response_model=ICD10CodingResponse)
async def reject_icd10_coding(
    icd10_coding_id: UUID,
    use_case: RejectUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ICD10CodingResponse:
    await use_case.execute(RejectICD10CodingInput(icd10_coding_id=icd10_coding_id))
    return await _get_response(icd10_coding_id, query_service, current_user)
