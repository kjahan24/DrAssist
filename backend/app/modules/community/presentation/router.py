"""HTTP routes for the Community module.

Follows the pattern established in `app.modules.organization.api.router`.
Every endpoint depends on `CurrentUser` and is scoped to the caller's own
`organization_id` — there is no "create a community for another
organization" endpoint (unlike `POST /organizations`, communities are
created *within* an already-provisioned tenant, so by definition a
caller is always already authenticated into one).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.community.application.dto import (
    CreateCommunityInput,
    DeleteCommunityInput,
    JoinCommunityInput,
    LeaveCommunityInput,
    UpdateCommunityInput,
)
from app.modules.community.domain.enums import CommunityVisibility
from app.modules.community.presentation.dependencies import (
    CreateCommunityUseCase,
    DeleteCommunityUseCase,
    GetCommunityQS,
    JoinCommunityUseCase,
    LeaveCommunityUseCase,
    ListCommunitiesQS,
    UpdateCommunityUseCase,
)
from app.modules.community.presentation.schemas import (
    CommunityMemberResponse,
    CommunityResponse,
    CreateCommunityRequest,
    UpdateCommunityRequest,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_COMMUNITY_SEARCH_SORT_FIELDS = frozenset({"created_at", "updated_at", "name", "slug"})


@router.get("/health")
async def get_community_health() -> dict[str, str]:
    return {"status": "ok", "module": "community"}


# --- Community -----------------------------------------------------------


@router.post("", response_model=CommunityResponse, status_code=status.HTTP_201_CREATED)
async def create_community(
    body: CreateCommunityRequest,
    use_case: CreateCommunityUseCase,
    query_service: GetCommunityQS,
    current_user: CurrentUser,
) -> CommunityResponse:
    output = await use_case.execute(
        CreateCommunityInput(
            organization_id=current_user.organization_id,
            created_by=current_user.user_id,
            **body.model_dump(),
        )
    )
    summary = await query_service.get_by_id(output.community_id)
    assert summary is not None
    return CommunityResponse.model_validate(summary)


@router.get("/{community_id}", response_model=CommunityResponse)
async def get_community(
    community_id: UUID, query_service: GetCommunityQS, current_user: CurrentUser
) -> CommunityResponse:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)
    return CommunityResponse.model_validate(summary)


@router.get("", response_model=PaginatedResponse[CommunityResponse])
async def list_communities(
    query_service: ListCommunitiesQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    visibility: Annotated[list[CommunityVisibility] | None, Query(alias="visibility")] = None,
) -> PaginatedResponse[CommunityResponse]:
    sort_field = resolve_sort_field(
        sorting.sort_by,
        allowed_sort_fields=_COMMUNITY_SEARCH_SORT_FIELDS,
        default_field="created_at",
    )
    result = await query_service.list_communities(
        organization_id=current_user.organization_id,
        query=filters.q,
        visibilities=visibility,
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
    items = [CommunityResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


@router.patch("/{community_id}", response_model=CommunityResponse)
async def update_community(
    community_id: UUID,
    body: UpdateCommunityRequest,
    use_case: UpdateCommunityUseCase,
    query_service: GetCommunityQS,
    current_user: CurrentUser,
) -> CommunityResponse:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        UpdateCommunityInput(
            community_id=community_id, acting_user_id=current_user.user_id, **body.model_dump()
        )
    )
    updated = await query_service.get_by_id(community_id)
    assert updated is not None
    return CommunityResponse.model_validate(updated)


@router.delete("/{community_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community(
    community_id: UUID,
    use_case: DeleteCommunityUseCase,
    query_service: GetCommunityQS,
    current_user: CurrentUser,
) -> None:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        DeleteCommunityInput(community_id=community_id, acting_user_id=current_user.user_id)
    )


# --- Membership ------------------------------------------------------------


@router.post(
    "/{community_id}/join", response_model=CommunityMemberResponse, status_code=status.HTTP_200_OK
)
async def join_community(
    community_id: UUID,
    use_case: JoinCommunityUseCase,
    query_service: GetCommunityQS,
    current_user: CurrentUser,
) -> CommunityMemberResponse:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)

    output = await use_case.execute(
        JoinCommunityInput(community_id=community_id, user_id=current_user.user_id)
    )
    return CommunityMemberResponse(
        id=output.member_id,
        community_id=output.community_id,
        user_id=output.user_id,
        role=output.role,
        status=output.status,
        joined_at=output.joined_at,
    )


@router.post("/{community_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_community(
    community_id: UUID,
    use_case: LeaveCommunityUseCase,
    query_service: GetCommunityQS,
    current_user: CurrentUser,
) -> None:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        LeaveCommunityInput(community_id=community_id, user_id=current_user.user_id)
    )
