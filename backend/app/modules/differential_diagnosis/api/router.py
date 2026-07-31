"""HTTP routes for the Differential Diagnosis module.

Follows the pattern established in
`app.modules.clinical_reasoning.api.router` — the two modules are
identically shaped (one-to-many with `ClinicalNote`, same review-workflow
transitions).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.differential_diagnosis.api.dependencies import (
    get_approve_differential_diagnosis_use_case,
    get_create_differential_diagnosis_use_case,
    get_differential_diagnosis_query_service,
    get_mark_differential_diagnosis_reviewed_use_case,
    get_reject_differential_diagnosis_use_case,
    get_update_differential_diagnosis_use_case,
)
from app.modules.differential_diagnosis.api.schemas import (
    CreateDifferentialDiagnosisRequest,
    DifferentialDiagnosisResponse,
    UpdateDifferentialDiagnosisRequest,
)
from app.modules.differential_diagnosis.application.dto import (
    ApproveDifferentialDiagnosisInput,
    CreateDifferentialDiagnosisInput,
    MarkDifferentialDiagnosisReviewedInput,
    RejectDifferentialDiagnosisInput,
    UpdateDifferentialDiagnosisInput,
)
from app.modules.differential_diagnosis.application.services.differential_diagnosis_query_service import (  # noqa: E501
    DifferentialDiagnosisQueryService,
)
from app.modules.differential_diagnosis.application.use_cases.approve_differential_diagnosis import (  # noqa: E501
    ApproveDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.application.use_cases.create_differential_diagnosis import (  # noqa: E501
    CreateDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.application.use_cases.mark_differential_diagnosis_reviewed import (  # noqa: E501
    MarkDifferentialDiagnosisReviewed,
)
from app.modules.differential_diagnosis.application.use_cases.reject_differential_diagnosis import (  # noqa: E501
    RejectDifferentialDiagnosis,
)
from app.modules.differential_diagnosis.application.use_cases.update_differential_diagnosis import (  # noqa: E501
    UpdateDifferentialDiagnosis,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"ranking", "diagnosis_source", "review_status", "excluded"})

QueryService = Annotated[
    DifferentialDiagnosisQueryService, Depends(get_differential_diagnosis_query_service)
]
CreateUseCase = Annotated[
    CreateDifferentialDiagnosis, Depends(get_create_differential_diagnosis_use_case)
]
UpdateUseCase = Annotated[
    UpdateDifferentialDiagnosis, Depends(get_update_differential_diagnosis_use_case)
]
MarkReviewedUseCase = Annotated[
    MarkDifferentialDiagnosisReviewed, Depends(get_mark_differential_diagnosis_reviewed_use_case)
]
ApproveUseCase = Annotated[
    ApproveDifferentialDiagnosis, Depends(get_approve_differential_diagnosis_use_case)
]
RejectUseCase = Annotated[
    RejectDifferentialDiagnosis, Depends(get_reject_differential_diagnosis_use_case)
]


async def _get_response(
    differential_diagnosis_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> DifferentialDiagnosisResponse:
    summary = await query_service.get_differential_diagnosis_summary(differential_diagnosis_id)
    if summary is None:
        raise NotFoundError(f"no differential diagnosis found with id {differential_diagnosis_id}")
    response = DifferentialDiagnosisResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("", response_model=DifferentialDiagnosisResponse, status_code=status.HTTP_201_CREATED)
async def create_differential_diagnosis(
    body: CreateDifferentialDiagnosisRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DifferentialDiagnosisResponse:
    output = await use_case.execute(
        CreateDifferentialDiagnosisInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response(output.differential_diagnosis_id, query_service, current_user)


@router.get("/{differential_diagnosis_id}", response_model=DifferentialDiagnosisResponse)
async def get_differential_diagnosis(
    differential_diagnosis_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> DifferentialDiagnosisResponse:
    return await _get_response(differential_diagnosis_id, query_service, current_user)


@router.get(
    "/clinical-note/{clinical_note_id}",
    response_model=PaginatedResponse[DifferentialDiagnosisResponse],
)
async def list_differential_diagnoses_for_clinical_note(
    clinical_note_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DifferentialDiagnosisResponse]:
    summaries = await query_service.list_differential_diagnoses_for_clinical_note(clinical_note_id)
    items = [DifferentialDiagnosisResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get(
    "/patient/{patient_id}", response_model=PaginatedResponse[DifferentialDiagnosisResponse]
)
async def list_differential_diagnoses_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[DifferentialDiagnosisResponse]:
    summaries = await query_service.list_differential_diagnoses_for_patient(patient_id)
    items = [DifferentialDiagnosisResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.put("/{differential_diagnosis_id}", response_model=DifferentialDiagnosisResponse)
async def update_differential_diagnosis(
    differential_diagnosis_id: UUID,
    body: UpdateDifferentialDiagnosisRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DifferentialDiagnosisResponse:
    await use_case.execute(
        UpdateDifferentialDiagnosisInput(
            differential_diagnosis_id=differential_diagnosis_id, **body.model_dump()
        )
    )
    return await _get_response(differential_diagnosis_id, query_service, current_user)


@router.patch(
    "/{differential_diagnosis_id}/mark-reviewed", response_model=DifferentialDiagnosisResponse
)
async def mark_differential_diagnosis_reviewed(
    differential_diagnosis_id: UUID,
    use_case: MarkReviewedUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DifferentialDiagnosisResponse:
    await use_case.execute(
        MarkDifferentialDiagnosisReviewedInput(differential_diagnosis_id=differential_diagnosis_id)
    )
    return await _get_response(differential_diagnosis_id, query_service, current_user)


@router.patch("/{differential_diagnosis_id}/approve", response_model=DifferentialDiagnosisResponse)
async def approve_differential_diagnosis(
    differential_diagnosis_id: UUID,
    use_case: ApproveUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DifferentialDiagnosisResponse:
    await use_case.execute(
        ApproveDifferentialDiagnosisInput(differential_diagnosis_id=differential_diagnosis_id)
    )
    return await _get_response(differential_diagnosis_id, query_service, current_user)


@router.patch("/{differential_diagnosis_id}/reject", response_model=DifferentialDiagnosisResponse)
async def reject_differential_diagnosis(
    differential_diagnosis_id: UUID,
    use_case: RejectUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> DifferentialDiagnosisResponse:
    await use_case.execute(
        RejectDifferentialDiagnosisInput(differential_diagnosis_id=differential_diagnosis_id)
    )
    return await _get_response(differential_diagnosis_id, query_service, current_user)
