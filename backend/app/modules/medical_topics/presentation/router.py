"""HTTP routes for the Medical Topics module.

Follows the pattern established in `app.modules.community.presentation
.router`. This module is platform-wide (not organization-scoped — see
`MedicalTopicRepository`'s own docstring), so unlike Community's router,
no endpoint here calls `ensure_same_organization`. `POST ""`,
`PATCH/DELETE "/{topic_id}"`, `POST "/specialties"`, and the alias/
relation management endpoints are gated by
`Depends(require_permission("topics.write"))` — there is no per-resource
ownership model for topics to check instead (unlike Community's per-
community `CommunityRole`), so a single platform-level permission code is
the only available authorization mechanism (see `CreateTopicService`'s
own docstring). `POST "/{topic_id}/feature"` uses the narrower
`topics.feature` permission, the same split
`app.modules.community.presentation.router` already establishes between
its own general write access and `communities.feature`/
`communities.verify`. `Follow`/`Unfollow` need no permission gate — a
normal end-user action open to any authenticated caller (see
`FollowTopicService`'s own docstring).

Route registration order matters for the literal-path GET endpoints
(`/search`, `/trending`, `/featured`, `/specialties`): each must be
registered *before* `GET /{topic_id}`, or Starlette would match e.g.
`/topics/search` as `topic_id="search"` first — see
`app.modules.community.presentation.router`'s own identical note.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, require_permission
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.authentication.public.dto import AuthenticatedPrincipalDTO
from app.modules.medical_topics.application.dto import (
    CreateTopicAliasInput,
    CreateTopicInput,
    CreateTopicRelationInput,
    CreateTopicSpecialtyInput,
    DeleteTopicAliasInput,
    DeleteTopicInput,
    DeleteTopicRelationInput,
    FeaturedTopicsInput,
    FollowTopicInput,
    ListTopicsInput,
    RelatedTopicsInput,
    SearchTopicsInput,
    SetTopicFeaturedInput,
    TrendingTopicsInput,
    UnfollowTopicInput,
    UpdateTopicInput,
)
from app.modules.medical_topics.presentation.dependencies import (
    CreateTopicSpecialtyUseCase,
    CreateTopicUseCase,
    DeleteTopicUseCase,
    FeaturedTopicsUseCase,
    FollowTopicUseCase,
    GetTopicQS,
    ListTopicsQS,
    ManageTopicAliasesUseCase,
    ManageTopicRelationsUseCase,
    RelatedTopicsUseCase,
    SearchTopicsUseCase,
    TopicFollowerQS,
    TopicSpecialtyQS,
    TrendingTopicsUseCase,
    UnfollowTopicUseCase,
    UpdateTopicUseCase,
)
from app.modules.medical_topics.presentation.schemas import (
    CreateTopicAliasRequest,
    CreateTopicRelationRequest,
    CreateTopicRequest,
    CreateTopicSpecialtyRequest,
    SetTopicFeaturedRequest,
    TopicAliasResponse,
    TopicFollowerResponse,
    TopicRelationResponse,
    TopicResponse,
    TopicSearchResponse,
    TopicSpecialtyResponse,
    UpdateTopicRequest,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_TOPIC_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "name", "trending_score", "popularity_score"}
)


@router.get("/health")
async def get_medical_topics_health() -> dict[str, str]:
    return {"status": "ok", "module": "medical_topics"}


# --- Discovery: search / trending / featured / specialties --------------------------


@router.get("/search", response_model=TopicSearchResponse)
async def search_topics(
    use_case: SearchTopicsUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
    q: str = Query(min_length=1, max_length=200),
    specialty_id: UUID | None = None,
) -> TopicSearchResponse:
    result = await use_case.search(
        SearchTopicsInput(
            query=q, specialty_id=specialty_id, offset=pagination.offset, limit=pagination.limit
        )
    )
    return TopicSearchResponse(
        items=[TopicResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/trending", response_model=TopicSearchResponse)
async def get_trending_topics(
    use_case: TrendingTopicsUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
    specialty_id: UUID | None = None,
) -> TopicSearchResponse:
    result = await use_case.get_trending(
        TrendingTopicsInput(
            specialty_id=specialty_id, offset=pagination.offset, limit=pagination.limit
        )
    )
    return TopicSearchResponse(
        items=[TopicResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/featured", response_model=TopicSearchResponse)
async def list_featured_topics(
    use_case: FeaturedTopicsUseCase, current_user: CurrentUser, pagination: Pagination
) -> TopicSearchResponse:
    result = await use_case.list_featured(
        FeaturedTopicsInput(offset=pagination.offset, limit=pagination.limit)
    )
    return TopicSearchResponse(
        items=[TopicResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/specialties", response_model=list[TopicSpecialtyResponse])
async def list_topic_specialties(query_service: TopicSpecialtyQS) -> list[TopicSpecialtyResponse]:
    specialties = await query_service.list_active(limit=100)
    return [TopicSpecialtyResponse.model_validate(s) for s in specialties]


@router.post(
    "/specialties", response_model=TopicSpecialtyResponse, status_code=status.HTTP_201_CREATED
)
async def create_topic_specialty(
    body: CreateTopicSpecialtyRequest,
    use_case: CreateTopicSpecialtyUseCase,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> TopicSpecialtyResponse:
    output = await use_case.execute(CreateTopicSpecialtyInput(**body.model_dump()))
    return TopicSpecialtyResponse(
        id=output.specialty_id, name=output.name, slug=output.slug, is_active=True
    )


# --- Topic -----------------------------------------------------------------------


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    body: CreateTopicRequest,
    use_case: CreateTopicUseCase,
    query_service: GetTopicQS,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> TopicResponse:
    output = await use_case.execute(
        CreateTopicInput(created_by=writer.user_id, **body.model_dump())
    )
    summary = await query_service.get_by_id(output.topic_id)
    assert summary is not None
    return TopicResponse.model_validate(summary)


@router.get("", response_model=PaginatedResponse[TopicResponse])
async def list_topics(
    query_service: ListTopicsQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    specialty_id: UUID | None = None,
    parent_id: UUID | None = None,
) -> PaginatedResponse[TopicResponse]:
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_TOPIC_SORT_FIELDS, default_field="created_at"
    )
    result = await query_service.list_topics(
        ListTopicsInput(
            query=filters.q,
            specialty_id=specialty_id,
            parent_id=parent_id,
            include_deleted=filters.include_deleted,
            sort_by=sort_field,
            sort_order=sorting.sort_order,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    items = [TopicResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(
    topic_id: UUID, query_service: GetTopicQS, current_user: CurrentUser
) -> TopicResponse:
    summary = await query_service.get_by_id(topic_id)
    if summary is None:
        raise NotFoundError(f"no topic found with id {topic_id}")
    return TopicResponse.model_validate(summary)


@router.patch("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: UUID,
    body: UpdateTopicRequest,
    use_case: UpdateTopicUseCase,
    query_service: GetTopicQS,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> TopicResponse:
    summary = await query_service.get_by_id(topic_id)
    if summary is None:
        raise NotFoundError(f"no topic found with id {topic_id}")

    await use_case.execute(
        UpdateTopicInput(topic_id=topic_id, updated_by=writer.user_id, **body.model_dump())
    )
    updated = await query_service.get_by_id(topic_id)
    assert updated is not None
    return TopicResponse.model_validate(updated)


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: UUID,
    use_case: DeleteTopicUseCase,
    query_service: GetTopicQS,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> None:
    summary = await query_service.get_by_id(topic_id)
    if summary is None:
        raise NotFoundError(f"no topic found with id {topic_id}")

    await use_case.execute(DeleteTopicInput(topic_id=topic_id))


@router.get("/{topic_id}/children", response_model=list[TopicResponse])
async def list_topic_children(
    topic_id: UUID, query_service: ListTopicsQS, current_user: CurrentUser, pagination: Pagination
) -> list[TopicResponse]:
    children = await query_service.list_children(
        topic_id, offset=pagination.offset, limit=pagination.limit
    )
    return [TopicResponse.model_validate(c) for c in children]


# --- Platform-level curation (featured) ------------------------------------------------


@router.post("/{topic_id}/feature", status_code=status.HTTP_204_NO_CONTENT)
async def set_topic_featured(
    topic_id: UUID,
    body: SetTopicFeaturedRequest,
    use_case: FeaturedTopicsUseCase,
    curator: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.feature"))],
) -> None:
    await use_case.set_featured(SetTopicFeaturedInput(topic_id=topic_id, featured=body.featured))


# --- Followers ---------------------------------------------------------------------------


@router.post("/{topic_id}/follow", status_code=status.HTTP_200_OK)
async def follow_topic(
    topic_id: UUID, use_case: FollowTopicUseCase, current_user: CurrentUser
) -> TopicFollowerResponse:
    output = await use_case.execute(
        FollowTopicInput(topic_id=topic_id, user_id=current_user.user_id)
    )
    return TopicFollowerResponse(
        id=output.follower_id,
        topic_id=output.topic_id,
        user_id=output.user_id,
        followed_at=output.followed_at,
    )


@router.post("/{topic_id}/unfollow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_topic(
    topic_id: UUID, use_case: UnfollowTopicUseCase, current_user: CurrentUser
) -> None:
    await use_case.execute(UnfollowTopicInput(topic_id=topic_id, user_id=current_user.user_id))


@router.get("/{topic_id}/followers", response_model=list[TopicFollowerResponse])
async def list_topic_followers(
    topic_id: UUID,
    query_service: TopicFollowerQS,
    current_user: CurrentUser,
    pagination: Pagination,
) -> list[TopicFollowerResponse]:
    followers = await query_service.list_followers(
        topic_id, offset=pagination.offset, limit=pagination.limit
    )
    return [TopicFollowerResponse.model_validate(f) for f in followers]


# --- Related topics ------------------------------------------------------------------------


@router.get("/{topic_id}/related", response_model=list[TopicResponse])
async def get_related_topics(
    topic_id: UUID,
    use_case: RelatedTopicsUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
) -> list[TopicResponse]:
    result = await use_case.get_related(
        RelatedTopicsInput(topic_id=topic_id, limit=pagination.limit)
    )
    return [TopicResponse.model_validate(s) for s in result.items]


@router.get("/{topic_id}/relations", response_model=list[TopicRelationResponse])
async def list_topic_relations(
    topic_id: UUID, use_case: ManageTopicRelationsUseCase
) -> list[TopicRelationResponse]:
    relations = await use_case.list_relations(topic_id)
    return [TopicRelationResponse.model_validate(r) for r in relations]


@router.post(
    "/{topic_id}/relations",
    response_model=TopicRelationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic_relation(
    topic_id: UUID,
    body: CreateTopicRelationRequest,
    use_case: ManageTopicRelationsUseCase,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> TopicRelationResponse:
    relation = await use_case.add_relation(
        CreateTopicRelationInput(topic_id=topic_id, **body.model_dump())
    )
    return TopicRelationResponse.model_validate(relation)


@router.delete("/{topic_id}/relations/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic_relation(
    topic_id: UUID,
    relation_id: UUID,
    use_case: ManageTopicRelationsUseCase,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> None:
    await use_case.delete_relation(DeleteTopicRelationInput(relation_id=relation_id))


# --- Aliases / synonyms -------------------------------------------------------------------


@router.get("/{topic_id}/aliases", response_model=list[TopicAliasResponse])
async def list_topic_aliases(
    topic_id: UUID, use_case: ManageTopicAliasesUseCase
) -> list[TopicAliasResponse]:
    aliases = await use_case.list_aliases(topic_id)
    return [TopicAliasResponse.model_validate(a) for a in aliases]


@router.post(
    "/{topic_id}/aliases", response_model=TopicAliasResponse, status_code=status.HTTP_201_CREATED
)
async def create_topic_alias(
    topic_id: UUID,
    body: CreateTopicAliasRequest,
    use_case: ManageTopicAliasesUseCase,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> TopicAliasResponse:
    alias = await use_case.create_alias(CreateTopicAliasInput(topic_id=topic_id, alias=body.alias))
    return TopicAliasResponse.model_validate(alias)


@router.delete("/{topic_id}/aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic_alias(
    topic_id: UUID,
    alias_id: UUID,
    use_case: ManageTopicAliasesUseCase,
    writer: Annotated[AuthenticatedPrincipalDTO, Depends(require_permission("topics.write"))],
) -> None:
    await use_case.delete_alias(DeleteTopicAliasInput(alias_id=alias_id))
