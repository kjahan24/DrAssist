"""HTTP routes for the SOAP Notes module.

`SOAPNote` is 1:1 with `ClinicalNote`, so the natural lookup key is
`clinical_note_id`, not the SOAP note's own id — `GET` uses
`/soap-notes/clinical-note/{clinical_note_id}`; `PUT` still addresses the
SOAP note by its own id, matching `UpdateSOAPNoteInput.soap_note_id`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.soap_notes.api.dependencies import (
    get_create_soap_note_use_case,
    get_soap_note_query_service,
    get_update_soap_note_use_case,
)
from app.modules.soap_notes.api.schemas import (
    CreateSOAPNoteRequest,
    SOAPNoteResponse,
    UpdateSOAPNoteRequest,
)
from app.modules.soap_notes.application.dto import CreateSOAPNoteInput, UpdateSOAPNoteInput
from app.modules.soap_notes.application.services.soap_note_query_service import (
    SOAPNoteQueryService,
)
from app.modules.soap_notes.application.use_cases.create_soap_note import CreateSOAPNote
from app.modules.soap_notes.application.use_cases.update_soap_note import UpdateSOAPNote
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SEARCH_SORT_FIELDS = frozenset({"created_at", "updated_at"})

QueryService = Annotated[SOAPNoteQueryService, Depends(get_soap_note_query_service)]
CreateUseCase = Annotated[CreateSOAPNote, Depends(get_create_soap_note_use_case)]
UpdateUseCase = Annotated[UpdateSOAPNote, Depends(get_update_soap_note_use_case)]


@router.post("", response_model=SOAPNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_soap_note(
    body: CreateSOAPNoteRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> SOAPNoteResponse:
    output = await use_case.execute(
        CreateSOAPNoteInput(**body.model_dump(), created_by=current_user.user_id)
    )
    summary = await query_service.get_soap_note_summary(output.clinical_note_id)
    assert summary is not None
    return SOAPNoteResponse.model_validate(summary)


@router.get("/clinical-note/{clinical_note_id}", response_model=SOAPNoteResponse)
async def get_soap_note_for_clinical_note(
    clinical_note_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> SOAPNoteResponse:
    summary = await query_service.get_soap_note_summary(clinical_note_id)
    if summary is None:
        raise NotFoundError(f"no SOAP note found for clinical note {clinical_note_id}")
    response = SOAPNoteResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("", response_model=PaginatedResponse[SOAPNoteResponse])
async def search_soap_notes(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
    visit_id: UUID | None = None,
) -> PaginatedResponse[SOAPNoteResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over SOAP notes — the module's first
    collection-listing endpoint (previously only single-record lookup by
    `clinical_note_id` existed). See `SOAPNoteRepository.search`'s
    docstring for how `filters.q` is matched."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SEARCH_SORT_FIELDS, default_field="created_at"
    )
    summaries, total = await query_service.search_soap_notes(
        organization_id=current_user.organization_id,
        query=filters.q,
        patient_id=patient_id,
        doctor_id=doctor_id,
        visit_id=visit_id,
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
    items = [SOAPNoteResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


@router.put("/{soap_note_id}", response_model=SOAPNoteResponse)
async def update_soap_note(
    soap_note_id: UUID,
    body: UpdateSOAPNoteRequest,
    use_case: UpdateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> SOAPNoteResponse:
    output = await use_case.execute(
        UpdateSOAPNoteInput(soap_note_id=soap_note_id, **body.model_dump())
    )
    summary = await query_service.get_soap_note_summary(output.clinical_note_id)
    assert summary is not None
    response = SOAPNoteResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response
