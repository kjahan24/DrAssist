"""HTTP routes for the Community Posts module.

Follows the pattern established in `app.modules.community.presentation
.router`/`app.modules.medical_topics.presentation.router`. Every endpoint
depends on `CurrentUser`, and every endpoint that resolves a specific
post also calls `ensure_same_organization` against that post's own
`organization_id` — multi-tenancy is enforced per-post here (posts are
tenant-scoped through their parent community), the same way Community's
own router enforces it per-community.

`POST ""`, `PATCH/DELETE "/{post_id}"`, `POST "/{post_id}/publish"`,
`POST "/{post_id}/archive"`, and the topic/tag/attachment management
endpoints are author-or-moderator authorized *inside* their own
application service (`_authorization.ensure_can_author_action` — this
module has no per-community role to check at the router layer the way
`require_permission` checks a global RBAC code, since "moderator of
*this* post's community" is inherently per-resource, the same reasoning
`app.modules.community.presentation.router` already gives for handling
its own community-role checks inside services rather than router-level
dependencies). `POST "/{post_id}/pin"`, `POST "/{post_id}/lock"`, and
`POST "/{post_id}/feature"` are moderator-only, also enforced inside
their own service (`_authorization.ensure_is_moderator`).

Route registration order matters only for same-segment-count literal-path
GET endpoints (`/search`, `/drafts`) — each must be registered *before*
`GET /{post_id}`, or Starlette would match e.g. `/community-posts/search`
as `post_id="search"` first — see `app.modules.community.presentation
.router`'s own identical note. `/feed/...` endpoints have a different
segment count than `/{post_id}` and can never collide with it regardless
of order, but are kept above it anyway for readability.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.community_posts.application.dto import (
    AddPostAttachmentInput,
    ArchivePostInput,
    AssignPostTagInput,
    AssignPostTopicInput,
    BrowseAuthorPostsInput,
    BrowseCommunityFeedInput,
    BrowseTopicFeedInput,
    CreatePostInput,
    DeletePostInput,
    ListPostsInput,
    PublishPostInput,
    RemovePostAttachmentInput,
    SearchPostsInput,
    SetPostFeaturedInput,
    SetPostLockedInput,
    SetPostPinnedInput,
    UnassignPostTagInput,
    UnassignPostTopicInput,
    UpdatePostInput,
)
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.presentation.dependencies import (
    ArchivePostUseCase,
    BrowseAuthorPostsUseCase,
    BrowseCommunityFeedUseCase,
    BrowseTopicFeedUseCase,
    CreatePostUseCase,
    DeletePostUseCase,
    FeaturePostUseCase,
    GetPostQS,
    ListPostsQS,
    LockPostUseCase,
    ManagePostAttachmentsUseCase,
    ManagePostTagsUseCase,
    ManagePostTopicsUseCase,
    PinPostUseCase,
    PublishPostUseCase,
    SearchPostsUseCase,
    UpdatePostUseCase,
)
from app.modules.community_posts.presentation.schemas import (
    AddPostAttachmentRequest,
    AssignPostTagRequest,
    AssignPostTopicRequest,
    CreatePostRequest,
    PostAttachmentResponse,
    PostFeedResponse,
    PostResponse,
    PostSearchResponse,
    PostTagResponse,
    PostTopicResponse,
    SetPostFeaturedRequest,
    SetPostLockedRequest,
    SetPostPinnedRequest,
    UpdatePostRequest,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_POST_SORT_FIELDS = frozenset({"created_at", "updated_at", "published_at", "title", "view_count"})


@router.get("/health")
async def get_community_posts_health() -> dict[str, str]:
    return {"status": "ok", "module": "community_posts"}


# --- Search / drafts ---------------------------------------------------------------


@router.get("/search", response_model=PostSearchResponse)
async def search_posts(
    use_case: SearchPostsUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
    q: str = Query(min_length=1, max_length=200),
    community_id: UUID | None = None,
    topic_id: UUID | None = None,
    author_id: UUID | None = None,
    post_type: Annotated[list[PostType] | None, Query(alias="post_type")] = None,
    status_filter: Annotated[list[PostStatus] | None, Query(alias="status")] = None,
    visibility: Annotated[list[PostVisibility] | None, Query(alias="visibility")] = None,
    pinned_only: bool = False,
    featured_only: bool = False,
) -> PostSearchResponse:
    result = await use_case.search(
        SearchPostsInput(
            organization_id=current_user.organization_id,
            query=q,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            post_type=tuple(post_type) if post_type else None,
            status=tuple(status_filter) if status_filter else None,
            visibility=tuple(visibility) if visibility else None,
            pinned_only=pinned_only,
            featured_only=featured_only,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    return PostSearchResponse(
        items=[PostResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/drafts", response_model=PaginatedResponse[PostResponse])
async def list_my_drafts(
    query_service: ListPostsQS, current_user: CurrentUser, pagination: Pagination
) -> PaginatedResponse[PostResponse]:
    result = await query_service.list_posts(
        ListPostsInput(
            organization_id=current_user.organization_id,
            author_id=current_user.user_id,
            status=(PostStatus.DRAFT,),
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    items = [PostResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


# --- Feeds (cursor-paged) -----------------------------------------------------------


@router.get("/feed/community/{community_id}", response_model=PostFeedResponse)
async def browse_community_feed(
    community_id: UUID,
    use_case: BrowseCommunityFeedUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> PostFeedResponse:
    result = await use_case.browse(
        BrowseCommunityFeedInput(community_id=community_id, cursor=cursor, limit=limit)
    )
    return PostFeedResponse(
        items=[PostResponse.model_validate(s) for s in result.items], next_cursor=result.next_cursor
    )


@router.get("/feed/topic/{topic_id}", response_model=PostFeedResponse)
async def browse_topic_feed(
    topic_id: UUID,
    use_case: BrowseTopicFeedUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> PostFeedResponse:
    result = await use_case.browse(
        BrowseTopicFeedInput(
            organization_id=current_user.organization_id,
            topic_id=topic_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return PostFeedResponse(
        items=[PostResponse.model_validate(s) for s in result.items], next_cursor=result.next_cursor
    )


@router.get("/feed/author/{author_id}", response_model=PostFeedResponse)
async def browse_author_posts(
    author_id: UUID,
    use_case: BrowseAuthorPostsUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> PostFeedResponse:
    result = await use_case.browse(
        BrowseAuthorPostsInput(
            organization_id=current_user.organization_id,
            author_id=author_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return PostFeedResponse(
        items=[PostResponse.model_validate(s) for s in result.items], next_cursor=result.next_cursor
    )


# --- Post ----------------------------------------------------------------------------


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: CreatePostRequest,
    use_case: CreatePostUseCase,
    query_service: GetPostQS,
    current_user: CurrentUser,
    community_id: UUID,
) -> PostResponse:
    output = await use_case.execute(
        CreatePostInput(
            community_id=community_id,
            author_id=current_user.user_id,
            title=body.title,
            body=body.body,
            slug=body.slug,
            excerpt=body.excerpt,
            post_type=body.post_type,
            visibility=body.visibility,
            is_anonymous=body.is_anonymous,
            featured_image_document_id=body.featured_image_document_id,
            topic_ids=tuple(body.topic_ids),
            tags=tuple(body.tags),
        )
    )
    summary = await query_service.get_by_id(output.post_id, acting_user_id=current_user.user_id)
    assert summary is not None
    return PostResponse.model_validate(summary)


@router.get("", response_model=PaginatedResponse[PostResponse])
async def list_posts(
    query_service: ListPostsQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    community_id: UUID | None = None,
    topic_id: UUID | None = None,
    author_id: UUID | None = None,
    post_type: Annotated[list[PostType] | None, Query(alias="post_type")] = None,
    status_filter: Annotated[list[PostStatus] | None, Query(alias="status")] = None,
    pinned_only: bool = False,
    featured_only: bool = False,
) -> PaginatedResponse[PostResponse]:
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_POST_SORT_FIELDS, default_field="created_at"
    )
    result = await query_service.list_posts(
        ListPostsInput(
            organization_id=current_user.organization_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            post_type=tuple(post_type) if post_type else None,
            status=tuple(status_filter) if status_filter else None,
            pinned_only=pinned_only,
            featured_only=featured_only,
            created_from=filters.created_from,
            created_to=filters.created_to,
            query=filters.q,
            include_deleted=filters.include_deleted,
            sort_by=sort_field,
            sort_order=sorting.sort_order,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    items = [PostResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: UUID, query_service: GetPostQS, current_user: CurrentUser
) -> PostResponse:
    summary = await query_service.get_by_id(post_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no post found with id {post_id}")
    ensure_same_organization(summary.organization_id, current_user)
    return PostResponse.model_validate(summary)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: UUID,
    body: UpdatePostRequest,
    use_case: UpdatePostUseCase,
    query_service: GetPostQS,
    current_user: CurrentUser,
) -> PostResponse:
    summary = await query_service.get_by_id(post_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no post found with id {post_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        UpdatePostInput(post_id=post_id, acting_user_id=current_user.user_id, **body.model_dump())
    )
    updated = await query_service.get_by_id(post_id, acting_user_id=current_user.user_id)
    assert updated is not None
    return PostResponse.model_validate(updated)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID, use_case: DeletePostUseCase, query_service: GetPostQS, current_user: CurrentUser
) -> None:
    summary = await query_service.get_by_id(post_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no post found with id {post_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(DeletePostInput(post_id=post_id, acting_user_id=current_user.user_id))


# --- Lifecycle: publish / archive ----------------------------------------------------


@router.post("/{post_id}/publish", response_model=PostResponse)
async def publish_post(
    post_id: UUID, use_case: PublishPostUseCase, current_user: CurrentUser
) -> PostResponse:
    summary = await use_case.execute(
        PublishPostInput(post_id=post_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return PostResponse.model_validate(summary)


@router.post("/{post_id}/archive", response_model=PostResponse)
async def archive_post(
    post_id: UUID, use_case: ArchivePostUseCase, current_user: CurrentUser
) -> PostResponse:
    summary = await use_case.execute(
        ArchivePostInput(post_id=post_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return PostResponse.model_validate(summary)


# --- Moderation: pin / lock / feature -------------------------------------------------


@router.post("/{post_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_post_pinned(
    post_id: UUID, body: SetPostPinnedRequest, use_case: PinPostUseCase, current_user: CurrentUser
) -> None:
    await use_case.execute(
        SetPostPinnedInput(post_id=post_id, acting_user_id=current_user.user_id, pinned=body.pinned)
    )


@router.post("/{post_id}/lock", status_code=status.HTTP_204_NO_CONTENT)
async def set_post_locked(
    post_id: UUID, body: SetPostLockedRequest, use_case: LockPostUseCase, current_user: CurrentUser
) -> None:
    await use_case.execute(
        SetPostLockedInput(post_id=post_id, acting_user_id=current_user.user_id, locked=body.locked)
    )


@router.post("/{post_id}/feature", status_code=status.HTTP_204_NO_CONTENT)
async def set_post_featured(
    post_id: UUID,
    body: SetPostFeaturedRequest,
    use_case: FeaturePostUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.execute(
        SetPostFeaturedInput(
            post_id=post_id, acting_user_id=current_user.user_id, featured=body.featured
        )
    )


# --- Topics ----------------------------------------------------------------------------


@router.get("/{post_id}/topics", response_model=list[PostTopicResponse])
async def list_post_topics(
    post_id: UUID, use_case: ManagePostTopicsUseCase
) -> list[PostTopicResponse]:
    assignments = await use_case.list_topics(post_id)
    return [PostTopicResponse.model_validate(a) for a in assignments]


@router.post(
    "/{post_id}/topics", response_model=PostTopicResponse, status_code=status.HTTP_201_CREATED
)
async def assign_post_topic(
    post_id: UUID,
    body: AssignPostTopicRequest,
    use_case: ManagePostTopicsUseCase,
    current_user: CurrentUser,
) -> PostTopicResponse:
    assignment = await use_case.assign_topic(
        AssignPostTopicInput(
            post_id=post_id, acting_user_id=current_user.user_id, topic_id=body.topic_id
        )
    )
    return PostTopicResponse.model_validate(assignment)


@router.delete("/{post_id}/topics/{post_topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_post_topic(
    post_id: UUID,
    post_topic_id: UUID,
    use_case: ManagePostTopicsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.unassign_topic(
        UnassignPostTopicInput(
            post_id=post_id, acting_user_id=current_user.user_id, post_topic_id=post_topic_id
        )
    )


# --- Tags ------------------------------------------------------------------------------


@router.get("/{post_id}/tags", response_model=list[PostTagResponse])
async def list_post_tags(post_id: UUID, use_case: ManagePostTagsUseCase) -> list[PostTagResponse]:
    assignments = await use_case.list_tags(post_id)
    return [PostTagResponse.model_validate(a) for a in assignments]


@router.post("/{post_id}/tags", response_model=PostTagResponse, status_code=status.HTTP_201_CREATED)
async def assign_post_tag(
    post_id: UUID,
    body: AssignPostTagRequest,
    use_case: ManagePostTagsUseCase,
    current_user: CurrentUser,
) -> PostTagResponse:
    assignment = await use_case.assign_tag(
        AssignPostTagInput(post_id=post_id, acting_user_id=current_user.user_id, tag=body.tag)
    )
    return PostTagResponse.model_validate(assignment)


@router.delete("/{post_id}/tags/{post_tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_post_tag(
    post_id: UUID, post_tag_id: UUID, use_case: ManagePostTagsUseCase, current_user: CurrentUser
) -> None:
    await use_case.unassign_tag(
        UnassignPostTagInput(
            post_id=post_id, acting_user_id=current_user.user_id, post_tag_id=post_tag_id
        )
    )


# --- Attachments --------------------------------------------------------------------------


@router.get("/{post_id}/attachments", response_model=list[PostAttachmentResponse])
async def list_post_attachments(
    post_id: UUID, use_case: ManagePostAttachmentsUseCase
) -> list[PostAttachmentResponse]:
    attachments = await use_case.list_attachments(post_id)
    return [PostAttachmentResponse.model_validate(a) for a in attachments]


@router.post(
    "/{post_id}/attachments",
    response_model=PostAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_post_attachment(
    post_id: UUID,
    body: AddPostAttachmentRequest,
    use_case: ManagePostAttachmentsUseCase,
    current_user: CurrentUser,
) -> PostAttachmentResponse:
    attachment = await use_case.add_attachment(
        AddPostAttachmentInput(
            post_id=post_id, acting_user_id=current_user.user_id, document_id=body.document_id
        )
    )
    return PostAttachmentResponse.model_validate(attachment)


@router.delete("/{post_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_post_attachment(
    post_id: UUID,
    attachment_id: UUID,
    use_case: ManagePostAttachmentsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.remove_attachment(
        RemovePostAttachmentInput(
            post_id=post_id, acting_user_id=current_user.user_id, attachment_id=attachment_id
        )
    )
