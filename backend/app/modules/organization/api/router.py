"""HTTP routes for the Organization module.

Follows the pattern established in `app.modules.patient.api.router`.
`POST /organizations` is the one endpoint in the whole API that does not
depend on `CurrentUser`: it provisions a brand new tenant, so by
definition no authenticated principal can yet belong to it. Every other
endpoint here operates on an *existing* organization and requires
`CurrentUser`, with `ensure_same_organization` applied so a caller can
only read their own organization's data.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.organization.api.dependencies import (
    get_create_department_use_case,
    get_create_organization_use_case,
    get_department_query_service,
    get_organization_query_service,
    get_update_organization_settings_use_case,
)
from app.modules.organization.api.schemas import (
    CreateDepartmentRequest,
    CreateOrganizationRequest,
    DepartmentResponse,
    OrganizationResponse,
    OrganizationSettingsResponse,
    UpdateOrganizationSettingsRequest,
)
from app.modules.organization.application.dto import (
    CreateDepartmentInput,
    CreateOrganizationInput,
    UpdateOrganizationSettingsInput,
)
from app.modules.organization.application.services.organization_query_service import (
    DepartmentQueryService,
    OrganizationQueryService,
)
from app.modules.organization.application.use_cases.create_department import CreateDepartment
from app.modules.organization.application.use_cases.create_organization import CreateOrganization
from app.modules.organization.application.use_cases.update_organization_settings import (
    UpdateOrganizationSettings,
)
from app.modules.organization.domain.enums import DepartmentStatus
from app.schemas.base import PaginatedResponse

router = APIRouter()

_DEPARTMENT_SEARCH_SORT_FIELDS = frozenset({"created_at", "updated_at", "name", "status"})

OrganizationQS = Annotated[OrganizationQueryService, Depends(get_organization_query_service)]
DepartmentQS = Annotated[DepartmentQueryService, Depends(get_department_query_service)]

CreateOrganizationUseCase = Annotated[CreateOrganization, Depends(get_create_organization_use_case)]
UpdateSettingsUseCase = Annotated[
    UpdateOrganizationSettings, Depends(get_update_organization_settings_use_case)
]
CreateDepartmentUseCase = Annotated[CreateDepartment, Depends(get_create_department_use_case)]


# --- Organization ----------------------------------------------------------


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: CreateOrganizationRequest,
    use_case: CreateOrganizationUseCase,
    query_service: OrganizationQS,
) -> OrganizationResponse:
    output = await use_case.execute(CreateOrganizationInput(**body.model_dump()))
    summary = await query_service.get_organization_summary(output.organization_id)
    assert summary is not None
    return OrganizationResponse.model_validate(summary)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID, query_service: OrganizationQS, current_user: CurrentUser
) -> OrganizationResponse:
    summary = await query_service.get_organization_summary(organization_id)
    if summary is None:
        raise NotFoundError(f"no organization found with id {organization_id}")
    response = OrganizationResponse.model_validate(summary)
    ensure_same_organization(response.id, current_user)
    return response


# --- Settings ----------------------------------------------------------------


@router.get("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    organization_id: UUID, query_service: OrganizationQS, current_user: CurrentUser
) -> OrganizationSettingsResponse:
    ensure_same_organization(organization_id, current_user)
    summary = await query_service.get_organization_settings_summary(organization_id)
    if summary is None:
        raise NotFoundError(f"no settings found for organization {organization_id}")
    return OrganizationSettingsResponse.model_validate(summary)


@router.patch("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    organization_id: UUID,
    body: UpdateOrganizationSettingsRequest,
    use_case: UpdateSettingsUseCase,
    query_service: OrganizationQS,
    current_user: CurrentUser,
) -> OrganizationSettingsResponse:
    ensure_same_organization(organization_id, current_user)
    await use_case.execute(
        UpdateOrganizationSettingsInput(
            organization_id=organization_id,
            **body.model_dump(),
            updated_by=current_user.user_id,
        )
    )
    summary = await query_service.get_organization_settings_summary(organization_id)
    assert summary is not None
    return OrganizationSettingsResponse.model_validate(summary)


# --- Departments -------------------------------------------------------------


@router.post("/{organization_id}/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    organization_id: UUID,
    body: CreateDepartmentRequest,
    use_case: CreateDepartmentUseCase,
    query_service: DepartmentQS,
    current_user: CurrentUser,
) -> DepartmentResponse:
    ensure_same_organization(organization_id, current_user)
    output = await use_case.execute(
        CreateDepartmentInput(organization_id=organization_id, **body.model_dump())
    )
    summary = await query_service.get_department_summary(output.department_id)
    assert summary is not None
    return DepartmentResponse.model_validate(summary)


@router.get("/{organization_id}/departments", response_model=PaginatedResponse[DepartmentResponse])
async def list_departments(
    organization_id: UUID,
    query_service: DepartmentQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[DepartmentStatus] | None, Query(alias="status")] = None,
) -> PaginatedResponse[DepartmentResponse]:
    """Search & Filtering module: this endpoint's shape (route, response,
    `offset`/`limit`/`sort_by`/`sort_order` params) is unchanged — it now
    also accepts `q`/`status`/`created_from`/`created_to`/`updated_from`/
    `updated_to`/`include_deleted`, and resolves them with a real SQL
    `WHERE`/`ORDER BY`/`OFFSET`/`LIMIT` query
    (`DepartmentQueryService.search_departments`) instead of fetching up
    to 1000 rows and paginating them in memory — see
    `DepartmentRepository.search`'s docstring for why "Organizations"
    search means searching departments in this single-tenant-per-request
    app."""
    ensure_same_organization(organization_id, current_user)
    sort_field = resolve_sort_field(
        sorting.sort_by,
        allowed_sort_fields=_DEPARTMENT_SEARCH_SORT_FIELDS,
        default_field="created_at",
    )
    summaries, total = await query_service.search_departments(
        organization_id=organization_id,
        query=filters.q,
        statuses=status_filter,
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
    items = [DepartmentResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )
