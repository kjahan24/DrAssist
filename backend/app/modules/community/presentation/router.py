"""HTTP routes for the Community module.

Follows the pattern established in `app.modules.organization.api.router`.
Every endpoint depends on `CurrentUser` and is scoped to the caller's own
`organization_id` — there is no "create a community for another
organization" endpoint (unlike `POST /organizations`, communities are
created *within* an already-provisioned tenant, so by definition a
caller is always already authenticated into one). `POST /categories`,
`POST /{id}/feature`, and `POST /{id}/verify` are the exceptions —
platform-wide actions, not organization-scoped ones (see
`CreateCommunityCategoryService`'s and `FeatureCommunitiesService`'s own
docstrings).

Route registration order matters for the literal-path GET endpoints
under `/community` (`/browse`, `/search`, `/featured`, `/categories`):
each must be registered *before* `GET /{community_id}`, or Starlette
would match e.g. `/community/browse` as `community_id="browse"` first —
see `docs/backend-architecture/11_standards_and_conventions.md`'s own
routing-order note. `POST /{community_id}/rules/reorder` has no such
ordering requirement (it's `POST`, while the `{rule_id}` routes below it
are `PATCH`/`DELETE` — different methods never collide), but is kept
above them anyway for readability.
"""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import CurrentUser, ensure_same_organization, require_permission
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.authentication.public.dto import AuthenticatedPrincipalDTO
from app.modules.community.application.dto import (
    AssignCommunityTagInput,
    BrowseCommunitiesInput,
    CreateCommunityCategoryInput,
    CreateCommunityInput,
    CreateCommunityRuleInput,
    DeleteCommunityInput,
    DeleteCommunityRuleInput,
    JoinCommunityInput,
    LeaveCommunityInput,
    ListFeaturedCommunitiesInput,
    ReorderCommunityRulesInput,
    SearchCommunitiesInput,
    SearchCommunityTagsInput,
    SetCommunityFeaturedInput,
    SetCommunityRuleEnabledInput,
    SetCommunityVerifiedInput,
    UnassignCommunityTagInput,
    UpdateCommunityAppearanceInput,
    UpdateCommunityInput,
    UpdateCommunityRuleInput,
)
from app.modules.community.domain.enums import CommunityVisibility
from app.modules.community.presentation.dependencies import (
    BrowseCommunitiesUseCase,
    CommunityCategoryQS,
    CommunityMembershipQS,
    CommunityStatisticsUseCase,
    CreateCommunityCategoryUseCase,
    CreateCommunityUseCase,
    DeleteCommunityUseCase,
    FeatureCommunitiesUseCase,
    GetCommunityQS,
    JoinCommunityUseCase,
    LeaveCommunityUseCase,
    ListCommunitiesQS,
    ManageCommunityRulesUseCase,
    ManageCommunityTagsUseCase,
    SearchCommunitiesUseCase,
    UpdateCommunityAppearanceUseCase,
    UpdateCommunityUseCase,
)
from app.modules.community.presentation.schemas import (
    AssignCommunityTagRequest,
    CommunityCategoryResponse,
    CommunityMemberResponse,
    CommunityResponse,
    CommunityRuleResponse,
    CommunitySearchResponse,
    CommunityStatisticsResponse,
    CommunityTagResponse,
    CommunityTagSearchResponse,
    CreateCommunityCategoryRequest,
    CreateCommunityRequest,
    CreateCommunityRuleRequest,
    ReorderCommunityRulesRequest,
    SetCommunityFeaturedRequest,
    SetCommunityRuleEnabledRequest,
    SetCommunityVerifiedRequest,
    UpdateCommunityRequest,
    UpdateCommunityRuleRequest,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_COMMUNITY_SEARCH_SORT_FIELDS = frozenset({"created_at", "updated_at", "name", "slug"})


@router.get("/health")
async def get_community_health() -> dict[str, str]:
    return {"status": "ok", "module": "community"}


# --- Discovery: browse / search / featured / categories ----------------------


@router.get("/browse", response_model=CommunitySearchResponse)
async def browse_communities(
    use_case: BrowseCommunitiesUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
    category_id: UUID | None = None,
    tag_id: Annotated[list[UUID] | None, Query(alias="tag_id")] = None,
    visibility: Annotated[list[CommunityVisibility] | None, Query(alias="visibility")] = None,
    sort: Literal["recent", "popular", "alphabetical"] = "recent",
) -> CommunitySearchResponse:
    result = await use_case.browse(
        BrowseCommunitiesInput(
            organization_id=current_user.organization_id,
            category_id=category_id,
            tag_ids=tuple(tag_id) if tag_id else (),
            visibilities=tuple(visibility) if visibility else None,
            sort=sort,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    return CommunitySearchResponse(
        items=[CommunityResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/search", response_model=CommunitySearchResponse)
async def search_communities(
    use_case: SearchCommunitiesUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
    q: str = Query(min_length=1, max_length=200),
    category_id: UUID | None = None,
    tag_id: Annotated[list[UUID] | None, Query(alias="tag_id")] = None,
) -> CommunitySearchResponse:
    result = await use_case.search(
        SearchCommunitiesInput(
            organization_id=current_user.organization_id,
            query=q,
            category_id=category_id,
            tag_ids=tuple(tag_id) if tag_id else (),
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    return CommunitySearchResponse(
        items=[CommunityResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/featured", response_model=CommunitySearchResponse)
async def list_featured_communities(
    use_case: FeatureCommunitiesUseCase, current_user: CurrentUser, pagination: Pagination
) -> CommunitySearchResponse:
    result = await use_case.list_featured(
        ListFeaturedCommunitiesInput(
            organization_id=current_user.organization_id,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    return CommunitySearchResponse(
        items=[CommunityResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/categories", response_model=list[CommunityCategoryResponse])
async def list_community_categories(
    query_service: CommunityCategoryQS,
) -> list[CommunityCategoryResponse]:
    categories = await query_service.list_active(limit=100)
    return [CommunityCategoryResponse.model_validate(c) for c in categories]


@router.post(
    "/categories", response_model=CommunityCategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_community_category(
    body: CreateCommunityCategoryRequest, use_case: CreateCommunityCategoryUseCase
) -> CommunityCategoryResponse:
    output = await use_case.execute(CreateCommunityCategoryInput(**body.model_dump()))
    return CommunityCategoryResponse(
        id=output.category_id, name=output.name, slug=output.slug, is_active=True
    )


@router.get("/tags/search", response_model=CommunityTagSearchResponse)
async def search_community_tags(
    use_case: ManageCommunityTagsUseCase,
    pagination: Pagination,
    q: str = Query(min_length=1, max_length=50),
) -> CommunityTagSearchResponse:
    result = await use_case.search_tags(
        SearchCommunityTagsInput(query=q, offset=pagination.offset, limit=pagination.limit)
    )
    return CommunityTagSearchResponse(
        items=[CommunityTagResponse.model_validate(t) for t in result.items], total=result.total
    )


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


@router.get("/{community_id}", response_model=CommunityResponse)
async def get_community(
    community_id: UUID, query_service: GetCommunityQS, current_user: CurrentUser
) -> CommunityResponse:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)
    return CommunityResponse.model_validate(summary)


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


@router.get("/{community_id}/moderators", response_model=list[CommunityMemberResponse])
async def list_community_moderators(
    community_id: UUID,
    query_service: GetCommunityQS,
    membership_query_service: CommunityMembershipQS,
    current_user: CurrentUser,
    pagination: Pagination,
) -> list[CommunityMemberResponse]:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)

    moderators = await membership_query_service.list_moderators(
        community_id, offset=pagination.offset, limit=pagination.limit
    )
    return [CommunityMemberResponse.model_validate(m) for m in moderators]


# --- Platform-level curation (featured/verified) ------------------------------


@router.post("/{community_id}/feature", status_code=status.HTTP_204_NO_CONTENT)
async def set_community_featured(
    community_id: UUID,
    body: SetCommunityFeaturedRequest,
    use_case: FeatureCommunitiesUseCase,
    moderator: Annotated[
        AuthenticatedPrincipalDTO, Depends(require_permission("communities.feature"))
    ],
) -> None:
    await use_case.set_featured(
        SetCommunityFeaturedInput(community_id=community_id, featured=body.featured)
    )


@router.post("/{community_id}/verify", status_code=status.HTTP_204_NO_CONTENT)
async def set_community_verified(
    community_id: UUID,
    body: SetCommunityVerifiedRequest,
    use_case: FeatureCommunitiesUseCase,
    moderator: Annotated[
        AuthenticatedPrincipalDTO, Depends(require_permission("communities.verify"))
    ],
) -> None:
    await use_case.set_verified(
        SetCommunityVerifiedInput(community_id=community_id, verified=body.verified)
    )


# --- Appearance ----------------------------------------------------------------


@router.put("/{community_id}/appearance", response_model=CommunityResponse)
async def update_community_appearance(
    community_id: UUID,
    use_case: UpdateCommunityAppearanceUseCase,
    query_service: GetCommunityQS,
    current_user: CurrentUser,
    avatar: UploadFile | None = File(default=None),
    banner: UploadFile | None = File(default=None),
) -> CommunityResponse:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        UpdateCommunityAppearanceInput(
            community_id=community_id,
            acting_user_id=current_user.user_id,
            avatar_data=await avatar.read() if avatar is not None else None,
            avatar_content_type=avatar.content_type if avatar is not None else None,
            avatar_filename=avatar.filename if avatar is not None else None,
            banner_data=await banner.read() if banner is not None else None,
            banner_content_type=banner.content_type if banner is not None else None,
            banner_filename=banner.filename if banner is not None else None,
        )
    )
    updated = await query_service.get_by_id(community_id)
    assert updated is not None
    return CommunityResponse.model_validate(updated)


# --- Statistics -------------------------------------------------------------------


@router.get("/{community_id}/statistics", response_model=CommunityStatisticsResponse)
async def get_community_statistics(
    community_id: UUID,
    use_case: CommunityStatisticsUseCase,
    query_service: GetCommunityQS,
    current_user: CurrentUser,
) -> CommunityStatisticsResponse:
    summary = await query_service.get_by_id(community_id)
    if summary is None:
        raise NotFoundError(f"no community found with id {community_id}")
    ensure_same_organization(summary.organization_id, current_user)

    stats = await use_case.get_statistics(community_id)
    return CommunityStatisticsResponse.model_validate(stats)


# --- Rules -------------------------------------------------------------------------


@router.get("/{community_id}/rules", response_model=list[CommunityRuleResponse])
async def list_community_rules(
    community_id: UUID, use_case: ManageCommunityRulesUseCase
) -> list[CommunityRuleResponse]:
    rules = await use_case.list_rules(community_id)
    return [CommunityRuleResponse.model_validate(r) for r in rules]


@router.post(
    "/{community_id}/rules",
    response_model=CommunityRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_community_rule(
    community_id: UUID,
    body: CreateCommunityRuleRequest,
    use_case: ManageCommunityRulesUseCase,
    current_user: CurrentUser,
) -> CommunityRuleResponse:
    output = await use_case.create_rule(
        CreateCommunityRuleInput(
            community_id=community_id, acting_user_id=current_user.user_id, **body.model_dump()
        )
    )
    return CommunityRuleResponse(
        id=output.rule_id,
        community_id=output.community_id,
        title=output.title,
        position=output.position,
        is_enabled=True,
    )


@router.post("/{community_id}/rules/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_community_rules(
    community_id: UUID,
    body: ReorderCommunityRulesRequest,
    use_case: ManageCommunityRulesUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.reorder(
        ReorderCommunityRulesInput(
            community_id=community_id,
            acting_user_id=current_user.user_id,
            ordered_rule_ids=body.ordered_rule_ids,
        )
    )


@router.patch("/{community_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_community_rule(
    community_id: UUID,
    rule_id: UUID,
    body: UpdateCommunityRuleRequest,
    use_case: ManageCommunityRulesUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.update_rule(
        UpdateCommunityRuleInput(
            rule_id=rule_id,
            community_id=community_id,
            acting_user_id=current_user.user_id,
            **body.model_dump(),
        )
    )


@router.patch("/{community_id}/rules/{rule_id}/enabled", status_code=status.HTTP_204_NO_CONTENT)
async def set_community_rule_enabled(
    community_id: UUID,
    rule_id: UUID,
    body: SetCommunityRuleEnabledRequest,
    use_case: ManageCommunityRulesUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.set_enabled(
        SetCommunityRuleEnabledInput(
            rule_id=rule_id,
            community_id=community_id,
            acting_user_id=current_user.user_id,
            enabled=body.enabled,
        )
    )


@router.delete("/{community_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community_rule(
    community_id: UUID,
    rule_id: UUID,
    use_case: ManageCommunityRulesUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.delete_rule(
        DeleteCommunityRuleInput(
            rule_id=rule_id, community_id=community_id, acting_user_id=current_user.user_id
        )
    )


# --- Tags --------------------------------------------------------------------------


@router.get("/{community_id}/tags", response_model=list[CommunityTagResponse])
async def list_community_tags(
    community_id: UUID, use_case: ManageCommunityTagsUseCase
) -> list[CommunityTagResponse]:
    tags = await use_case.list_tags_for_community(community_id)
    return [CommunityTagResponse.model_validate(t) for t in tags]


@router.post(
    "/{community_id}/tags", response_model=CommunityTagResponse, status_code=status.HTTP_201_CREATED
)
async def assign_community_tag(
    community_id: UUID,
    body: AssignCommunityTagRequest,
    use_case: ManageCommunityTagsUseCase,
    current_user: CurrentUser,
) -> CommunityTagResponse:
    tag = await use_case.assign_tag(
        AssignCommunityTagInput(
            community_id=community_id,
            acting_user_id=current_user.user_id,
            tag_name=body.tag_name,
        )
    )
    return CommunityTagResponse.model_validate(tag)


@router.delete("/{community_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_community_tag(
    community_id: UUID,
    tag_id: UUID,
    use_case: ManageCommunityTagsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.unassign_tag(
        UnassignCommunityTagInput(
            community_id=community_id, acting_user_id=current_user.user_id, tag_id=tag_id
        )
    )
