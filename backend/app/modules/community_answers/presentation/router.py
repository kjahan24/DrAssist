"""HTTP routes for the Community Answers module.

Follows the pattern established in `app.modules.community_questions
.presentation.router`. Every endpoint depends on `CurrentUser`, and every
endpoint that resolves a specific answer also calls
`ensure_same_organization` against that answer's own `organization_id` —
multi-tenancy is enforced per-answer here, the same way Community
Questions' own router enforces it per-question.

`POST ""`, `PATCH/DELETE "/{answer_id}"`, `POST "/{answer_id}/publish"`,
`POST "/{answer_id}/archive"`, `POST "/{answer_id}/restore"`, and the
attachment-management endpoints are author-or-moderator authorized
*inside* their own application service (`_authorization
.ensure_can_author_action`). `POST "/{answer_id}/feature"` and
`POST "/{answer_id}/pin"` are moderator-only, also enforced inside their
own service (`_authorization.ensure_is_moderator`).
`POST/DELETE "/{answer_id}/best"` are authorized inside their own service
via `_authorization.ensure_can_select_best_answer` — the *question's*
author (not the answer's), or a moderator — see that service's own
docstring.

Route registration order matters only for same-segment-count literal-path
GET endpoints (`/search`, `/drafts`) — each must be registered *before*
`GET /{answer_id}`, or Starlette would match e.g.
`/community-answers/search` as `answer_id="search"` first — see
`app.modules.community_questions.presentation.router`'s own identical
note. `/feed/...` endpoints have a different segment count than
`/{answer_id}` and can never collide with it regardless of order, but are
kept above it anyway for readability.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.community_answers.application.dto import (
    AddAnswerAttachmentInput,
    ArchiveAnswerInput,
    CreateAnswerInput,
    DeleteAnswerInput,
    ListAnswersInput,
    ListAuthorAnswersInput,
    ListQuestionAnswersInput,
    MarkBestAnswerInput,
    PublishAnswerInput,
    RemoveAnswerAttachmentInput,
    RemoveBestAnswerInput,
    RestoreAnswerInput,
    SearchAnswersInput,
    SetAnswerFeaturedInput,
    SetAnswerPinnedInput,
    UpdateAnswerInput,
)
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.presentation.dependencies import (
    AnswerRevisionQS,
    ArchiveAnswerUseCase,
    CreateAnswerUseCase,
    DeleteAnswerUseCase,
    FeatureAnswerUseCase,
    GetAnswerQS,
    ListAnswersQS,
    ListAuthorAnswersUseCase,
    ListQuestionAnswersUseCase,
    ManageAnswerAttachmentsUseCase,
    MarkBestAnswerUseCase,
    PinAnswerUseCase,
    PublishAnswerUseCase,
    RemoveBestAnswerUseCase,
    RestoreAnswerUseCase,
    SearchAnswersUseCase,
    UpdateAnswerUseCase,
)
from app.modules.community_answers.presentation.schemas import (
    AddAnswerAttachmentRequest,
    AnswerAttachmentResponse,
    AnswerFeedResponse,
    AnswerResponse,
    AnswerRevisionResponse,
    AnswerSearchResponse,
    CreateAnswerRequest,
    SetAnswerFeaturedRequest,
    SetAnswerPinnedRequest,
    UpdateAnswerRequest,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_ANSWER_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "published_at", "view_count", "share_count"}
)


@router.get("/health")
async def get_community_answers_health() -> dict[str, str]:
    return {"status": "ok", "module": "community_answers"}


# --- Search / drafts ---------------------------------------------------------------


@router.get("/search", response_model=AnswerSearchResponse)
async def search_answers(
    use_case: SearchAnswersUseCase,
    current_user: CurrentUser,
    pagination: Pagination,
    q: str = Query(min_length=1, max_length=200),
    question_id: UUID | None = None,
    community_id: UUID | None = None,
    topic_id: UUID | None = None,
    author_id: UUID | None = None,
    status_filter: Annotated[list[AnswerStatus] | None, Query(alias="status")] = None,
    visibility: Annotated[list[AnswerVisibility] | None, Query(alias="visibility")] = None,
    best_answer_only: bool = False,
    featured_only: bool = False,
    pinned_only: bool = False,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> AnswerSearchResponse:
    result = await use_case.search(
        SearchAnswersInput(
            organization_id=current_user.organization_id,
            query=q,
            question_id=question_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            status=tuple(status_filter) if status_filter else None,
            visibility=tuple(visibility) if visibility else None,
            best_answer_only=best_answer_only,
            featured_only=featured_only,
            pinned_only=pinned_only,
            created_from=created_from,
            created_to=created_to,
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    return AnswerSearchResponse(
        items=[AnswerResponse.model_validate(s) for s in result.items], total=result.total
    )


@router.get("/drafts", response_model=PaginatedResponse[AnswerResponse])
async def list_my_drafts(
    query_service: ListAnswersQS, current_user: CurrentUser, pagination: Pagination
) -> PaginatedResponse[AnswerResponse]:
    result = await query_service.list_answers(
        ListAnswersInput(
            organization_id=current_user.organization_id,
            author_id=current_user.user_id,
            status=(AnswerStatus.DRAFT,),
            offset=pagination.offset,
            limit=pagination.limit,
        )
    )
    items = [AnswerResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


# --- Feeds (cursor-paged) -----------------------------------------------------------


@router.get("/feed/question/{question_id}", response_model=AnswerFeedResponse)
async def list_question_answers(
    question_id: UUID,
    use_case: ListQuestionAnswersUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> AnswerFeedResponse:
    result = await use_case.list_answers(
        ListQuestionAnswersInput(
            organization_id=current_user.organization_id,
            question_id=question_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return AnswerFeedResponse(
        items=[AnswerResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


@router.get("/feed/author/{author_id}", response_model=AnswerFeedResponse)
async def list_author_answers(
    author_id: UUID,
    use_case: ListAuthorAnswersUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> AnswerFeedResponse:
    result = await use_case.list_answers(
        ListAuthorAnswersInput(
            organization_id=current_user.organization_id,
            author_id=author_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return AnswerFeedResponse(
        items=[AnswerResponse.model_validate(s) for s in result.items],
        next_cursor=result.next_cursor,
    )


# --- Answer --------------------------------------------------------------------------


@router.post("", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
async def create_answer(
    body: CreateAnswerRequest,
    use_case: CreateAnswerUseCase,
    query_service: GetAnswerQS,
    current_user: CurrentUser,
    question_id: UUID,
) -> AnswerResponse:
    output = await use_case.execute(
        CreateAnswerInput(
            question_id=question_id,
            author_id=current_user.user_id,
            body=body.body,
            summary=body.summary,
            visibility=body.visibility,
            is_anonymous=body.is_anonymous,
        )
    )
    summary = await query_service.get_by_id(output.answer_id, acting_user_id=current_user.user_id)
    assert summary is not None
    return AnswerResponse.model_validate(summary)


@router.get("", response_model=PaginatedResponse[AnswerResponse])
async def list_answers(
    query_service: ListAnswersQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    question_id: UUID | None = None,
    community_id: UUID | None = None,
    topic_id: UUID | None = None,
    author_id: UUID | None = None,
    status_filter: Annotated[list[AnswerStatus] | None, Query(alias="status")] = None,
    best_answer_only: bool = False,
    featured_only: bool = False,
    pinned_only: bool = False,
) -> PaginatedResponse[AnswerResponse]:
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_ANSWER_SORT_FIELDS, default_field="created_at"
    )
    result = await query_service.list_answers(
        ListAnswersInput(
            organization_id=current_user.organization_id,
            question_id=question_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            status=tuple(status_filter) if status_filter else None,
            best_answer_only=best_answer_only,
            featured_only=featured_only,
            pinned_only=pinned_only,
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
    items = [AnswerResponse.model_validate(summary) for summary in result.items]
    return PaginatedResponse(
        items=items, total=result.total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/{answer_id}", response_model=AnswerResponse)
async def get_answer(
    answer_id: UUID, query_service: GetAnswerQS, current_user: CurrentUser
) -> AnswerResponse:
    summary = await query_service.get_by_id(answer_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no answer found with id {answer_id}")
    ensure_same_organization(summary.organization_id, current_user)
    return AnswerResponse.model_validate(summary)


@router.patch("/{answer_id}", response_model=AnswerResponse)
async def update_answer(
    answer_id: UUID,
    body: UpdateAnswerRequest,
    use_case: UpdateAnswerUseCase,
    query_service: GetAnswerQS,
    current_user: CurrentUser,
) -> AnswerResponse:
    summary = await query_service.get_by_id(answer_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no answer found with id {answer_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        UpdateAnswerInput(
            answer_id=answer_id, acting_user_id=current_user.user_id, **body.model_dump()
        )
    )
    updated = await query_service.get_by_id(answer_id, acting_user_id=current_user.user_id)
    assert updated is not None
    return AnswerResponse.model_validate(updated)


@router.delete("/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_answer(
    answer_id: UUID,
    use_case: DeleteAnswerUseCase,
    query_service: GetAnswerQS,
    current_user: CurrentUser,
) -> None:
    summary = await query_service.get_by_id(answer_id, acting_user_id=current_user.user_id)
    if summary is None:
        raise NotFoundError(f"no answer found with id {answer_id}")
    ensure_same_organization(summary.organization_id, current_user)

    await use_case.execute(
        DeleteAnswerInput(answer_id=answer_id, acting_user_id=current_user.user_id)
    )


# --- Lifecycle: publish / archive / restore -------------------------------------------


@router.post("/{answer_id}/publish", response_model=AnswerResponse)
async def publish_answer(
    answer_id: UUID, use_case: PublishAnswerUseCase, current_user: CurrentUser
) -> AnswerResponse:
    summary = await use_case.execute(
        PublishAnswerInput(answer_id=answer_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return AnswerResponse.model_validate(summary)


@router.post("/{answer_id}/archive", response_model=AnswerResponse)
async def archive_answer(
    answer_id: UUID, use_case: ArchiveAnswerUseCase, current_user: CurrentUser
) -> AnswerResponse:
    summary = await use_case.execute(
        ArchiveAnswerInput(answer_id=answer_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return AnswerResponse.model_validate(summary)


@router.post("/{answer_id}/restore", response_model=AnswerResponse)
async def restore_answer(
    answer_id: UUID, use_case: RestoreAnswerUseCase, current_user: CurrentUser
) -> AnswerResponse:
    summary = await use_case.execute(
        RestoreAnswerInput(answer_id=answer_id, acting_user_id=current_user.user_id)
    )
    ensure_same_organization(summary.organization_id, current_user)
    return AnswerResponse.model_validate(summary)


# --- Best answer -----------------------------------------------------------------------


@router.post("/{answer_id}/best", response_model=AnswerResponse)
async def mark_best_answer(
    answer_id: UUID,
    use_case: MarkBestAnswerUseCase,
    current_user: CurrentUser,
    question_id: UUID,
) -> AnswerResponse:
    summary = await use_case.execute(
        MarkBestAnswerInput(
            question_id=question_id, answer_id=answer_id, acting_user_id=current_user.user_id
        )
    )
    ensure_same_organization(summary.organization_id, current_user)
    return AnswerResponse.model_validate(summary)


@router.delete("/{answer_id}/best", status_code=status.HTTP_204_NO_CONTENT)
async def remove_best_answer(
    answer_id: UUID,
    use_case: RemoveBestAnswerUseCase,
    current_user: CurrentUser,
    question_id: UUID,
) -> None:
    await use_case.execute(
        RemoveBestAnswerInput(
            question_id=question_id, answer_id=answer_id, acting_user_id=current_user.user_id
        )
    )


# --- Moderation: feature / pin ----------------------------------------------------------


@router.post("/{answer_id}/feature", status_code=status.HTTP_204_NO_CONTENT)
async def set_answer_featured(
    answer_id: UUID,
    body: SetAnswerFeaturedRequest,
    use_case: FeatureAnswerUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.execute(
        SetAnswerFeaturedInput(
            answer_id=answer_id, acting_user_id=current_user.user_id, featured=body.featured
        )
    )


@router.post("/{answer_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_answer_pinned(
    answer_id: UUID,
    body: SetAnswerPinnedRequest,
    use_case: PinAnswerUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.execute(
        SetAnswerPinnedInput(
            answer_id=answer_id, acting_user_id=current_user.user_id, pinned=body.pinned
        )
    )


# --- Attachments --------------------------------------------------------------------------


@router.get("/{answer_id}/attachments", response_model=list[AnswerAttachmentResponse])
async def list_answer_attachments(
    answer_id: UUID, use_case: ManageAnswerAttachmentsUseCase
) -> list[AnswerAttachmentResponse]:
    attachments = await use_case.list_attachments(answer_id)
    return [AnswerAttachmentResponse.model_validate(a) for a in attachments]


@router.post(
    "/{answer_id}/attachments",
    response_model=AnswerAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_answer_attachment(
    answer_id: UUID,
    body: AddAnswerAttachmentRequest,
    use_case: ManageAnswerAttachmentsUseCase,
    current_user: CurrentUser,
) -> AnswerAttachmentResponse:
    attachment = await use_case.add_attachment(
        AddAnswerAttachmentInput(
            answer_id=answer_id,
            acting_user_id=current_user.user_id,
            document_id=body.document_id,
        )
    )
    return AnswerAttachmentResponse.model_validate(attachment)


@router.delete("/{answer_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_answer_attachment(
    answer_id: UUID,
    attachment_id: UUID,
    use_case: ManageAnswerAttachmentsUseCase,
    current_user: CurrentUser,
) -> None:
    await use_case.remove_attachment(
        RemoveAnswerAttachmentInput(
            answer_id=answer_id,
            acting_user_id=current_user.user_id,
            attachment_id=attachment_id,
        )
    )


# --- Revision history --------------------------------------------------------------------


@router.get("/{answer_id}/revisions", response_model=list[AnswerRevisionResponse])
async def list_answer_revisions(
    answer_id: UUID, query_service: AnswerRevisionQS, pagination: Pagination
) -> list[AnswerRevisionResponse]:
    revisions = await query_service.list_revisions(
        answer_id, offset=pagination.offset, limit=pagination.limit
    )
    return [AnswerRevisionResponse.model_validate(r) for r in revisions]
