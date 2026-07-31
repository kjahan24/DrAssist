"""HTTP routes for the Clinical Notes module.

Follows the pattern established in `app.modules.diagnosis.api.router`.
Only `Create`/`Get`/`List` — the module's own use-case layer has no
sign/lock use case yet (only `CreateClinicalNote` exists), so there is
no status-transition action to wire up here.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.api.search_params import SearchFilters, resolve_sort_field
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
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus
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


@router.get("", response_model=PaginatedResponse[ClinicalNoteResponse])
async def search_clinical_notes(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[ClinicalNoteStatus] | None, Query(alias="status")] = None,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
    visit_id: UUID | None = None,
    encounter_from: datetime | None = None,
    encounter_to: datetime | None = None,
) -> PaginatedResponse[ClinicalNoteResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over clinical notes — see
    `ClinicalNoteRepository.search`'s docstring for how `filters.q`
    combines full-text and partial matching."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SORT_FIELDS, default_field="encounter_datetime"
    )
    summaries, total = await query_service.search_clinical_notes(
        organization_id=current_user.organization_id,
        query=filters.q,
        statuses=status_filter,
        patient_id=patient_id,
        doctor_id=doctor_id,
        visit_id=visit_id,
        encounter_from=encounter_from,
        encounter_to=encounter_to,
        created_from=filters.created_from,
        created_to=filters.created_to,
        updated_from=filters.updated_from,
        updated_to=filters.updated_to,
        include_deleted=filters.include_deleted,
        sort_by=sort_field,
        sort_order=sorting.sort_order,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    items = [ClinicalNoteResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


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
