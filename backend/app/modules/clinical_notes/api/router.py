"""HTTP routes for the Clinical Notes module.

Follows the pattern established in `app.modules.diagnosis.api.router`.
Only `Create`/`Get`/`List` — the module's own use-case layer has no
sign/lock use case yet (only `CreateClinicalNote` exists), so there is
no status-transition action to wire up here.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.clinical_notes.api.dependencies import (
    get_clinical_note_query_service,
    get_create_clinical_note_use_case,
)
from app.modules.clinical_notes.api.schemas import (
    ClinicalNoteResponse,
    CreateClinicalNoteRequest,
)
from app.modules.clinical_notes.application.dto import CreateClinicalNoteInput
from app.modules.clinical_notes.application.services.clinical_note_query_service import (
    ClinicalNoteQueryService,
)
from app.modules.clinical_notes.application.use_cases.create_clinical_note import (
    CreateClinicalNote,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"note_number", "note_type", "status", "encounter_datetime"})

QueryService = Annotated[ClinicalNoteQueryService, Depends(get_clinical_note_query_service)]
CreateUseCase = Annotated[CreateClinicalNote, Depends(get_create_clinical_note_use_case)]


@router.post("", response_model=ClinicalNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_clinical_note(
    body: CreateClinicalNoteRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> ClinicalNoteResponse:
    output = await use_case.execute(
        CreateClinicalNoteInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_clinical_note_summary(output.clinical_note_id)
    assert summary is not None
    return ClinicalNoteResponse.model_validate(summary)


@router.get("/{clinical_note_id}", response_model=ClinicalNoteResponse)
async def get_clinical_note(
    clinical_note_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> ClinicalNoteResponse:
    summary = await query_service.get_clinical_note_summary(clinical_note_id)
    if summary is None:
        raise NotFoundError(f"no clinical note found with id {clinical_note_id}")
    response = ClinicalNoteResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("/visit/{visit_id}", response_model=PaginatedResponse[ClinicalNoteResponse])
async def list_clinical_notes_for_visit(
    visit_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[ClinicalNoteResponse]:
    summaries = await query_service.list_clinical_notes_for_visit(visit_id)
    items = [ClinicalNoteResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/patient/{patient_id}", response_model=PaginatedResponse[ClinicalNoteResponse])
async def list_clinical_notes_for_patient(
    patient_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[ClinicalNoteResponse]:
    summaries = await query_service.list_clinical_notes_for_patient(patient_id)
    items = [ClinicalNoteResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )
