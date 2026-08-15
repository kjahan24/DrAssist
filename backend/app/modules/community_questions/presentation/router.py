"""HTTP routes for the Community Questions module.

Follows the pattern established in `app.modules.community_posts
.presentation.router`. Every endpoint depends on `CurrentUser`, and every
endpoint that resolves a specific question also calls
`ensure_same_organization` against that question's own `organization_id`
— multi-tenancy is enforced per-question here (questions are
tenant-scoped through their parent community), the same way Community
Posts' own router enforces it per-post.

`POST ""`, `PATCH/DELETE "/{question_id}"`, `POST "/{question_id}/publish"`,
`POST "/{question_id}/archive"`, `POST "/{question_id}/close"`,
`POST "/{question_id}/reopen"`, and the topic/tag/attachment management
endpoints are author-or-moderator authorized *inside* their own
application service (`_authorization.ensure_can_author_action`).
`POST "/{question_id}/pin"` and `POST "/{question_id}/feature"` are
moderator-only, also enforced inside their own service
(`_authorization.ensure_is_moderator`). `POST/DELETE "/{question_id}/follow"`
are viewability-gated inside their own service (`_authorization
.ensure_can_view`) — see `ManageQuestionFollowersService`'s own docstring.

Route registration order matters only for same-segment-count literal-path
GET endpoints (`/search`, `/drafts`) — each must be registered *before*
`GET /{question_id}`, or Starlette would match e.g.
`/community-questions/search` as `question_id="search"` first — see
`app.modules.community_posts.presentation.router`'s own identical note.
`/feed/...` endpoints have a different segment count than `/{question_id}`
and can never collide with it regardless of order, but are kept above it
anyway for readability.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.community_questions.application.dto import (
    AddQuestionAttachmentInput,
    ArchiveQuestionInput,
    AssignQuestionTagInput,
    AssignQuestionTopicInput,
    BrowseAuthorQuestionsInput,
    BrowseCommunityQuestionsInput,
    BrowseTopicQuestionsInput,
    CloseQuestionInput,
    CreateQuestionInput,
    DeleteQuestionInput,
    FollowQuestionInput,
    ListQuestionsInput,
    PublishQuestionInput,
    RemoveQuestionAttachmentInput,
    ReopenQuestionInput,
    SearchQuestionsInput,
    SetQuestionFeaturedInput,
    SetQuestionPinnedInput,
    UnassignQuestionTagInput,
    UnassignQuestionTopicInput,
    UnfollowQuestionInput,
    UpdateQuestionInput,
)
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.presentation.dependencies import (
    ArchiveQuestionUseCase,
    BrowseAuthorQuestionsUseCase,
    BrowseCommunityQuestionsUseCase,
    BrowseTopicQuestionsUseCase,
    CloseQuestionUseCase,
    CreateQuestionUseCase,
    DeleteQuestionUseCase,
    FeatureQuestionUseCase,
    GetQuestionQS,
    ListQuestionsQS,
    ManageQuestionAttachmentsUseCase,
    ManageQuestionFollowersUseCase,
    ManageQuestionTagsUseCase,
    ManageQuestionTopicsUseCase,
    PinQuestionUseCase,
    PublishQuestionUseCase,
    ReopenQuestionUseCase,
    SearchQuestionsUseCase,
    UpdateQuestionUseCase,
)
from app.modules.community_questions.presentation.schemas import (
    AddQuestionAttachmentRequest,
    AssignQuestionTagRequest,
    AssignQuestionTopicRequest,
    CreateQuestionRequest,
    QuestionAttachmentResponse,
    QuestionFeedResponse,
    QuestionFollowerResponse,
    QuestionResponse,
    QuestionSearchResponse,
    QuestionTagResponse,
    QuestionTopicResponse,
    SetQuestionFeaturedRequest,
    SetQuestionPinnedRequest,
    UpdateQuestionRequest,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_QUESTION_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "published_at", "title", "view_count", "follower_count"}
)


@router.get("/health")
async def get_community_questions_health() -> dict[str, str]:
    return {"status": "ok", "module": "community_questions"}


# --- Search / drafts ---------------------------------------------------------------


@router.get("/search", response_model=QuestionSearchResponse)
async def search_questions(
    use_case: SearchQuestionsUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
    q: str = Query(min_length=1, max_length=200),
    community_id: UUID | None = None,
    topic_id: UUID | None = None,
    author_id: UUID | None = None,
    question_type: Annotated[list[QuestionType] | None, Query(alias="question_type")] = None,
    status_filter: Annotated[list[QuestionStatus] | None, Query(alias="status")] = None,
    visibility: Annotated[list[QuestionVisibility] | None, Query(alias="visibility")] = None,
    pinned_only: bool = False,
    featured_only: bool = False,
) -> QuestionSearchResponse:
    result = await use_case.search(
        SearchQuestionsInput(
            organization_id=current_user.organization_id,
            query=q,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            question_type=tuple(question_type) if question_type else None,
            status=tuple(status_filter) if status_filter else None,
            visibility=tuple(visibility) if visibility else None,
            pinned_only=pinned_only,
            featured_only=featured_only,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    return QuestionSearchResponse(
        items=[QuestionResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/drafts", response_model=PaginatedResponse[QuestionResponse])
async def list_my_drafts(
    query_service: ListQuestionsQS, current_user: CurrentUser, pagination: Pagination
) -> PaginatedResponse[QuestionResponse]:
    result = await query_service.list_questions(
        ListQuestionsInput(
            organization_id=current_user.organization_id,
            author_id=current_user.user_id,
            status=(QuestionStatus.DRAFT,),
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    items = [QuestionResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


# --- Feeds (cursor-paged) -----------------------------------------------------------


@router.get("/feed/community/{community_id}", response_model=QuestionFeedResponse)
async def browse_community_questions(
    community_id: UUID,
    use_case: BrowseCommunityQuestionsUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> QuestionFeedResponse:
    result = await use_case.browse(
        BrowseCommunityQuestionsInput(community_id=community_id, cursor=cursor, limit=limit)
    )
    return QuestionFeedResponse(
        items=[QuestionResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


@router.get("/feed/topic/{topic_id}", response_model=QuestionFeedResponse)
async def browse_topic_questions(
    topic_id: UUID,
    use_case: BrowseTopicQuestionsUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> QuestionFeedResponse:
    result = await use_case.browse(
        BrowseTopicQuestionsInput(
            organization_id=current_user.organization_id,
            topic_id=topic_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return QuestionFeedResponse(
        items=[QuestionResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


@router.get("/feed/author/{author_id}", response_model=QuestionFeedResponse)
async def browse_author_questions(
    author_id: UUID,
    use_case: BrowseAuthorQuestionsUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> QuestionFeedResponse:
    result = await use_case.browse(
        BrowseAuthorQuestionsInput(
            organization_id=current_user.organization_id,
            author_id=author_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return QuestionFeedResponse(
        items=[QuestionResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


# --- Question --------------------------------------------------------------------------


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: CreateQuestionRequest,
    use_case: CreateQuestionUseCase,
    query_service: GetQuestionQS,
    current_user: CurrentUser,
    community_id: UUID,
) -> QuestionResponse:
    output = await use_case.execute(
        CreateQuestionInput(
            community_id=community_id,
            author_id=current_user.user_id,
            primary_topic_id=body.primary_topic_id,
            title=body.title,
            body=body.body,
            slug=body.slug,
            summary=body.summary,
            question_type=body.question_type,
            visibility=body.visibility,
            is_anonymous=body.is_anonymous,
            secondary_topic_ids=tuple(body.secondary_topic_ids),
            tags=tuple(body.tags),
        )
    )
    summary = await query_service.get_by_id(output.question_id, acting_user_id=current_user.user_id)
    assert summary is not None
    return QuestionResponse.model_validate(summary)


@router.get("", response_model=PaginatedResponse[QuestionResponse])
async def list_questions(
    query_service: ListQuestionsQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    community_id: UUID | None = None,
    topic_id: UUID | None = None,
    author_id: UUID | None = None,
    question_type: Annotated[list[QuestionType] | None, Query(alias="question_type")] = None,
    status_filter: Annotated[list[QuestionStatus] | None, Query(alias="status")] = None,
    pinned_only: bool = False,
    featured_only: bool = False,
) -> PaginatedResponse[QuestionResponse]:
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_QUESTION_SORT_FIELDS, default_field="created_at"
    )
    result = await query_service.list_questions(
        ListQuestionsInput(
            organization_id=current_user.organization_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            question_type=tuple(question_type) if question_type else None,
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
    items = [QuestionResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: UUID, query_service: GetQuestionQS, current_user: CurrentUser
) -> QuestionResponse:
    summary = await query_service.get_by_id(question_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no question found with id {question_id}")
    ensure_same_organization(summary.organization_id, current_user)
    return QuestionResponse.model_validate(summary)


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    body: UpdateQuestionRequest,
    use_case: UpdateQuestionUseCase,
    query_service: GetQuestionQS,
    current_user: CurrentUser,
) -> QuestionResponse:
    summary = await query_service.get_by_id(question_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no question found with id {question_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        UpdateQuestionInput(
            question_id=question_id, acting_user_id=current_user.user_id, **body.model_dump()
        )
    )
    updated = await query_service.get_by_id(question_id, acting_user_id=current_user.user_id)
    assert updated is not None
    return QuestionResponse.model_validate(updated)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: UUID,
    use_case: DeleteQuestionUseCase,
    query_service: GetQuestionQS,
    current_user: CurrentUser,
) -> None:
    summary = await query_service.get_by_id(question_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no question found with id {question_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        DeleteQuestionInput(question_id=question_id, acting_user_id=current_user.user_id)
    )


# --- Lifecycle: publish / archive / close / reopen -----------------------------------


@router.post("/{question_id}/publish", response_model=QuestionResponse)
async def publish_question(
    question_id: UUID, use_case: PublishQuestionUseCase, current_user: CurrentUser
) -> QuestionResponse:
    summary = await use_case.execute(
        PublishQuestionInput(question_id=question_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return QuestionResponse.model_validate(summary)


@router.post("/{question_id}/archive", response_model=QuestionResponse)
async def archive_question(
    question_id: UUID, use_case: ArchiveQuestionUseCase, current_user: CurrentUser
) -> QuestionResponse:
    summary = await use_case.execute(
        ArchiveQuestionInput(question_id=question_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return QuestionResponse.model_validate(summary)


@router.post("/{question_id}/close", response_model=QuestionResponse)
async def close_question(
    question_id: UUID, use_case: CloseQuestionUseCase, current_user: CurrentUser
) -> QuestionResponse:
    summary = await use_case.execute(
        CloseQuestionInput(question_id=question_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return QuestionResponse.model_validate(summary)


@router.post("/{question_id}/reopen", response_model=QuestionResponse)
async def reopen_question(
    question_id: UUID, use_case: ReopenQuestionUseCase, current_user: CurrentUser
) -> QuestionResponse:
    summary = await use_case.execute(
        ReopenQuestionInput(question_id=question_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return QuestionResponse.model_validate(summary)


# --- Moderation: pin / feature ---------------------------------------------------------


@router.post("/{question_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_question_pinned(
    question_id: UUID,
    body: SetQuestionPinnedRequest,
    use_case: PinQuestionUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.execute(
        SetQuestionPinnedInput(
            question_id=question_id, acting_user_id=current_user.user_id, pinned=body.pinned
        )
    )


@router.post("/{question_id}/feature", status_code=status.HTTP_204_NO_CONTENT)
async def set_question_featured(
    question_id: UUID,
    body: SetQuestionFeaturedRequest,
    use_case: FeatureQuestionUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.execute(
        SetQuestionFeaturedInput(
            question_id=question_id, acting_user_id=current_user.user_id, featured=body.featured
        )
    )


# --- Topics (secondary) -----------------------------------------------------------------


@router.get("/{question_id}/topics", response_model=list[QuestionTopicResponse])
async def list_question_topics(
    question_id: UUID, use_case: ManageQuestionTopicsUseCase
) -> list[QuestionTopicResponse]:
    assignments = await use_case.list_topics(question_id)
    return [QuestionTopicResponse.model_validate(a) for a in assignments]


@router.post(
    "/{question_id}/topics",
    response_model=QuestionTopicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_question_topic(
    question_id: UUID,
    body: AssignQuestionTopicRequest,
    use_case: ManageQuestionTopicsUseCase,
    current_user: CurrentUser,
) -> QuestionTopicResponse:
    assignment = await use_case.assign_topic(
        AssignQuestionTopicInput(
            question_id=question_id, acting_user_id=current_user.user_id, topic_id=body.topic_id
        )
    )
    return QuestionTopicResponse.model_validate(assignment)


@router.delete("/{question_id}/topics/{question_topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_question_topic(
    question_id: UUID,
    question_topic_id: UUID,
    use_case: ManageQuestionTopicsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.unassign_topic(
        UnassignQuestionTopicInput(
            question_id=question_id,
            acting_user_id=current_user.user_id,
            question_topic_id=question_topic_id,
        )
    )


# --- Tags ------------------------------------------------------------------------------


@router.get("/{question_id}/tags", response_model=list[QuestionTagResponse])
async def list_question_tags(
    question_id: UUID, use_case: ManageQuestionTagsUseCase
) -> list[QuestionTagResponse]:
    assignments = await use_case.list_tags(question_id)
    return [QuestionTagResponse.model_validate(a) for a in assignments]


@router.post(
    "/{question_id}/tags", response_model=QuestionTagResponse, status_code=status.HTTP_201_CREATED
)
async def assign_question_tag(
    question_id: UUID,
    body: AssignQuestionTagRequest,
    use_case: ManageQuestionTagsUseCase,
    current_user: CurrentUser,
) -> QuestionTagResponse:
    assignment = await use_case.assign_tag(
        AssignQuestionTagInput(
            question_id=question_id, acting_user_id=current_user.user_id, tag=body.tag
        )
    )
    return QuestionTagResponse.model_validate(assignment)


@router.delete("/{question_id}/tags/{question_tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_question_tag(
    question_id: UUID,
    question_tag_id: UUID,
    use_case: ManageQuestionTagsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.unassign_tag(
        UnassignQuestionTagInput(
            question_id=question_id,
            acting_user_id=current_user.user_id,
            question_tag_id=question_tag_id,
        )
    )


# --- Attachments --------------------------------------------------------------------------


@router.get("/{question_id}/attachments", response_model=list[QuestionAttachmentResponse])
async def list_question_attachments(
    question_id: UUID, use_case: ManageQuestionAttachmentsUseCase
) -> list[QuestionAttachmentResponse]:
    attachments = await use_case.list_attachments(question_id)
    return [QuestionAttachmentResponse.model_validate(a) for a in attachments]


@router.post(
    "/{question_id}/attachments",
    response_model=QuestionAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_question_attachment(
    question_id: UUID,
    body: AddQuestionAttachmentRequest,
    use_case: ManageQuestionAttachmentsUseCase,
    current_user: CurrentUser,
) -> QuestionAttachmentResponse:
    attachment = await use_case.add_attachment(
        AddQuestionAttachmentInput(
            question_id=question_id,
            acting_user_id=current_user.user_id,
            document_id=body.document_id,
        )
    )
    return QuestionAttachmentResponse.model_validate(attachment)


@router.delete("/{question_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_question_attachment(
    question_id: UUID,
    attachment_id: UUID,
    use_case: ManageQuestionAttachmentsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.remove_attachment(
        RemoveQuestionAttachmentInput(
            question_id=question_id,
            acting_user_id=current_user.user_id,
            attachment_id=attachment_id,
        )
    )


# --- Followers -------------------------------------------------------------------------


@router.get("/{question_id}/followers", response_model=list[QuestionFollowerResponse])
async def list_question_followers(
    question_id: UUID, use_case: ManageQuestionFollowersUseCase
) -> list[QuestionFollowerResponse]:
    followers = await use_case.list_followers(question_id)
    return [QuestionFollowerResponse.model_validate(f) for f in followers]


@router.post(
    "/{question_id}/follow",
    response_model=QuestionFollowerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def follow_question(
    question_id: UUID, use_case: ManageQuestionFollowersUseCase, current_user: CurrentUser
) -> QuestionFollowerResponse:
    follower = await use_case.follow(
        FollowQuestionInput(question_id=question_id, acting_user_id=current_user.user_id)
    )
    return QuestionFollowerResponse.model_validate(follower)


@router.delete("/{question_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_question(
    question_id: UUID, use_case: ManageQuestionFollowersUseCase, current_user: CurrentUser
) -> None:
    await use_case.unfollow(
        UnfollowQuestionInput(question_id=question_id, acting_user_id=current_user.user_id)
    )
