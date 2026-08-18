"""HTTP routes for the Community Comments module.

Follows the pattern established in `app.modules.community_answers
.presentation.router`. Every endpoint depends on `CurrentUser`, and every
endpoint that resolves a specific comment also calls
`ensure_same_organization` against that comment's own `organization_id`
— multi-tenancy is enforced per-comment here, the same way Community
Answers' own router enforces it per-answer.

There is only one PATCH/DELETE/publish/archive/restore route family
(`/{comment_id}/...`), used for *both* "Comment CRUD" and "Reply CRUD"
(this task's own API section names them separately) — see
`app.modules.community_comments.application.services`'s own package
docstring for why: a reply is a `CommunityComment` row like any other,
addressed by the same id space, so a second, functionally-identical
`/replies/{reply_id}` route family would just be a redundant alias.
`POST ""` (Comment CRUD's own create) and `POST "/{comment_id}/replies"`
(Reply CRUD's own create) are the two routes that *do* genuinely differ
— target-based vs. parent-based, matching `CreateCommentService`/
`CreateReplyService`'s own split.

Route registration order matters only for same-segment-count literal-path
GET endpoints (`/search`, `/drafts`) — each must be registered *before*
`GET /{comment_id}`, or Starlette would match e.g.
`/community-comments/search` as `comment_id="search"` first — see
`app.modules.community_answers.presentation.router`'s own identical
note. `/feed/...` endpoints have a different segment count than
`/{comment_id}` and can never collide with it regardless of order, but
are kept above it anyway for readability.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination
from app.core.exceptions import NotFoundError
from app.modules.community_comments.application.dto import (
    AddCommentAttachmentInput,
    ArchiveCommentInput,
    CreateCommentInput,
    CreateReplyInput,
    DeleteCommentInput,
    ListCommentsInput,
    ListRepliesInput,
    PublishCommentInput,
    RemoveCommentAttachmentInput,
    RestoreCommentInput,
    SearchCommentsInput,
    UpdateCommentInput,
)
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.presentation.dependencies import (
    ArchiveCommentUseCase,
    CommentRevisionQS,
    CreateCommentUseCase,
    CreateReplyUseCase,
    DeleteCommentUseCase,
    GetCommentQS,
    GetThreadUseCase,
    ListCommentsUseCase,
    ListRepliesUseCase,
    ManageCommentAttachmentsUseCase,
    PublishCommentUseCase,
    RestoreCommentUseCase,
    SearchCommentsUseCase,
    UpdateCommentUseCase,
)
from app.modules.community_comments.presentation.schemas import (
    AddCommentAttachmentRequest,
    CommentAttachmentResponse,
    CommentFeedResponse,
    CommentResponse,
    CommentRevisionResponse,
    CommentSearchResponse,
    CreateCommentRequest,
    CreateReplyRequest,
    ThreadResponse,
    UpdateCommentRequest,
)

router = APIRouter()


@router.get("/health")
async def get_community_comments_health() -> dict[str, str]:
    return {"status": "ok", "module": "community_comments"}


# --- Search / drafts ---------------------------------------------------------------


@router.get("/search", response_model=CommentSearchResponse)
async def search_comments(
    use_case: SearchCommentsUseCase,
    current_user: CurrentUser,
    q: str | None = Query(default=None, min_length=1, max_length=200),
    target_type: CommentTargetType | None = None,
    target_id: UUID | None = None,
    community_id: UUID | None = None,
    topic_id: UUID | None = None,
    author_id: UUID | None = None,
    parent_comment_id: UUID | None = None,
    top_level_only: bool = False,
    status_filter: list[CommentStatus] | None = Query(default=None, alias="status"),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> CommentSearchResponse:
    result = await use_case.search(
        SearchCommentsInput(
            organization_id=current_user.organization_id,
            query=q,
            target_type=target_type,
            target_id=target_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            parent_comment_id=parent_comment_id,
            top_level_only=top_level_only,
            status=tuple(status_filter) if status_filter else None,
            created_from=created_from,
            created_to=created_to,
            sort_order=sort_order,  # type: ignore[arg-type]
            cursor=cursor,
            limit=limit,
        )
    )
    return CommentSearchResponse(
        items=[CommentResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


@router.get("/drafts", response_model=CommentSearchResponse)
async def list_my_drafts(
    use_case: SearchCommentsUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> CommentSearchResponse:
    result = await use_case.search(
        SearchCommentsInput(
            organization_id=current_user.organization_id,
            author_id=current_user.user_id,
            status=(CommentStatus.DRAFT,),
            cursor=cursor,
            limit=limit,
        )
    )
    return CommentSearchResponse(
        items=[CommentResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


# --- Feeds (cursor-paged) -----------------------------------------------------------


@router.get("/feed/target/{target_type}/{target_id}", response_model=CommentFeedResponse)
async def list_comments(
    target_type: CommentTargetType,
    target_id: UUID,
    use_case: ListCommentsUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> CommentFeedResponse:
    result = await use_case.list_comments(
        ListCommentsInput(
            organization_id=current_user.organization_id,
            target_type=target_type,
            target_id=target_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return CommentFeedResponse(
        items=[CommentResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


# --- Comment (top-level create + unified CRUD) ----------------------------------------


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    body: CreateCommentRequest,
    use_case: CreateCommentUseCase,
    query_service: GetCommentQS,
    current_user: CurrentUser,
    target_type: CommentTargetType,
    target_id: UUID,
) -> CommentResponse:
    output = await use_case.execute(
        CreateCommentInput(
            target_type=target_type,
            target_id=target_id,
            author_id=current_user.user_id,
            body=body.body,
            is_anonymous=body.is_anonymous,
        )
    )
    summary = await query_service.get_by_id(output.comment_id, acting_user_id=current_user.user_id)
    assert summary is not None
    return CommentResponse.model_validate(summary)


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: UUID, query_service: GetCommentQS, current_user: CurrentUser
) -> CommentResponse:
    summary = await query_service.get_by_id(comment_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no comment found with id {comment_id}")
    ensure_same_organization(summary.organization_id, current_user)
    return CommentResponse.model_validate(summary)


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    body: UpdateCommentRequest,
    use_case: UpdateCommentUseCase,
    query_service: GetCommentQS,
    current_user: CurrentUser,
) -> CommentResponse:
    summary = await query_service.get_by_id(comment_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no comment found with id {comment_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        UpdateCommentInput(
            comment_id=comment_id, acting_user_id=current_user.user_id, **body.model_dump()
        )
    )
    updated = await query_service.get_by_id(comment_id, acting_user_id=current_user.user_id)
    assert updated is not None
    return CommentResponse.model_validate(updated)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    use_case: DeleteCommentUseCase,
    query_service: GetCommentQS,
    current_user: CurrentUser,
) -> None:
    summary = await query_service.get_by_id(comment_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no comment found with id {comment_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        DeleteCommentInput(comment_id=comment_id, acting_user_id=current_user.user_id)
    )


# --- Lifecycle: publish / archive / restore -------------------------------------------


@router.post("/{comment_id}/publish", response_model=CommentResponse)
async def publish_comment(
    comment_id: UUID, use_case: PublishCommentUseCase, current_user: CurrentUser
) -> CommentResponse:
    summary = await use_case.execute(
        PublishCommentInput(comment_id=comment_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return CommentResponse.model_validate(summary)


@router.post("/{comment_id}/archive", response_model=CommentResponse)
async def archive_comment(
    comment_id: UUID, use_case: ArchiveCommentUseCase, current_user: CurrentUser
) -> CommentResponse:
    summary = await use_case.execute(
        ArchiveCommentInput(comment_id=comment_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return CommentResponse.model_validate(summary)


@router.post("/{comment_id}/restore", response_model=CommentResponse)
async def restore_comment(
    comment_id: UUID, use_case: RestoreCommentUseCase, current_user: CurrentUser
) -> CommentResponse:
    summary = await use_case.execute(
        RestoreCommentInput(comment_id=comment_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return CommentResponse.model_validate(summary)


# --- Reply (nested create + threaded reads) --------------------------------------------


@router.post(
    "/{comment_id}/replies", response_model=CommentResponse, status_code=status.HTTP_201_CREATED
)
async def create_reply(
    comment_id: UUID,
    body: CreateReplyRequest,
    use_case: CreateReplyUseCase,
    query_service: GetCommentQS,
    current_user: CurrentUser,
) -> CommentResponse:
    output = await use_case.execute(
        CreateReplyInput(
            parent_comment_id=comment_id,
            author_id=current_user.user_id,
            body=body.body,
            is_anonymous=body.is_anonymous,
        )
    )
    summary = await query_service.get_by_id(output.comment_id, acting_user_id=current_user.user_id)
    assert summary is not None
    return CommentResponse.model_validate(summary)


@router.get("/{comment_id}/replies", response_model=CommentFeedResponse)
async def list_replies(
    comment_id: UUID,
    use_case: ListRepliesUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> CommentFeedResponse:
    result = await use_case.list_replies(
        ListRepliesInput(
            organization_id=current_user.organization_id,
            parent_comment_id=comment_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return CommentFeedResponse(
        items=[CommentResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


@router.get("/{comment_id}/thread", response_model=ThreadResponse)
async def get_thread(
    comment_id: UUID, use_case: GetThreadUseCase, current_user: CurrentUser
) -> ThreadResponse:
    result = await use_case.get_thread(comment_id)
    return ThreadResponse(items=[CommentResponse.model_validate(s) for s in result.items])


# --- Attachments --------------------------------------------------------------------------


@router.get("/{comment_id}/attachments", response_model=list[CommentAttachmentResponse])
async def list_comment_attachments(
    comment_id: UUID, use_case: ManageCommentAttachmentsUseCase
) -> list[CommentAttachmentResponse]:
    attachments = await use_case.list_attachments(comment_id)
    return [CommentAttachmentResponse.model_validate(a) for a in attachments]


@router.post(
    "/{comment_id}/attachments",
    response_model=CommentAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment_attachment(
    comment_id: UUID,
    body: AddCommentAttachmentRequest,
    use_case: ManageCommentAttachmentsUseCase,
    current_user: CurrentUser,
) -> CommentAttachmentResponse:
    attachment = await use_case.add_attachment(
        AddCommentAttachmentInput(
            comment_id=comment_id,
            acting_user_id=current_user.user_id,
            document_id=body.document_id,
        )
    )
    return CommentAttachmentResponse.model_validate(attachment)


@router.delete("/{comment_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_comment_attachment(
    comment_id: UUID,
    attachment_id: UUID,
    use_case: ManageCommentAttachmentsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.remove_attachment(
        RemoveCommentAttachmentInput(
            comment_id=comment_id,
            acting_user_id=current_user.user_id,
            attachment_id=attachment_id,
        )
    )


# --- Revision history --------------------------------------------------------------------


@router.get("/{comment_id}/revisions", response_model=list[CommentRevisionResponse])
async def list_comment_revisions(
    comment_id: UUID, query_service: CommentRevisionQS, pagination: Pagination
) -> list[CommentRevisionResponse]:
    revisions = await query_service.list_revisions(
        comment_id, offset=pagination.offset, limit=pagination.limit
    )
    return [CommentRevisionResponse.model_validate(r) for r in revisions]
