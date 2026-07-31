"""HTTP routes for the Notification module.

New — this module had no `api/` package before the REST APIs task (see
`container.py`'s scope note). Follows the pattern established in
`app.modules.appointment.api.router`. Status-transition actions:
`mark-sent`/`mark-delivered`/`mark-read`/`cancel`/`expire`, matching the
explicit transition map `domain/entities.py` enforces.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.notification.api.dependencies import (
    get_cancel_notification_use_case,
    get_create_notification_use_case,
    get_expire_notification_use_case,
    get_mark_notification_delivered_use_case,
    get_mark_notification_read_use_case,
    get_mark_notification_sent_use_case,
    get_notification_query_service,
)
from app.modules.notification.api.schemas import (
    CreateNotificationRequest,
    NotificationResponse,
)
from app.modules.notification.application.dto import (
    CancelNotificationInput,
    CreateNotificationInput,
    ExpireNotificationInput,
    MarkNotificationDeliveredInput,
    MarkNotificationReadInput,
    MarkNotificationSentInput,
)
from app.modules.notification.application.services.notification_query_service import (
    NotificationQueryService,
)
from app.modules.notification.application.use_cases.cancel_notification import CancelNotification
from app.modules.notification.application.use_cases.create_notification import CreateNotification
from app.modules.notification.application.use_cases.expire_notification import ExpireNotification
from app.modules.notification.application.use_cases.mark_notification_delivered import (
    MarkNotificationDelivered,
)
from app.modules.notification.application.use_cases.mark_notification_read import (
    MarkNotificationRead,
)
from app.modules.notification.application.use_cases.mark_notification_sent import (
    MarkNotificationSent,
)
from app.modules.notification.domain.enums import NotificationPriority, NotificationStatus
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"notification_type", "priority", "status", "scheduled_at"})

QueryService = Annotated[NotificationQueryService, Depends(get_notification_query_service)]
CreateUseCase = Annotated[CreateNotification, Depends(get_create_notification_use_case)]
MarkSentUseCase = Annotated[MarkNotificationSent, Depends(get_mark_notification_sent_use_case)]
MarkDeliveredUseCase = Annotated[
    MarkNotificationDelivered, Depends(get_mark_notification_delivered_use_case)
]
MarkReadUseCase = Annotated[MarkNotificationRead, Depends(get_mark_notification_read_use_case)]
CancelUseCase = Annotated[CancelNotification, Depends(get_cancel_notification_use_case)]
ExpireUseCase = Annotated[ExpireNotification, Depends(get_expire_notification_use_case)]


async def _get_response(
    notification_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> NotificationResponse:
    summary = await query_service.get_notification_summary(notification_id)
    if summary is None:
        raise NotFoundError(f"no notification found with id {notification_id}")
    response = NotificationResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    body: CreateNotificationRequest,
    use_case: CreateUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> NotificationResponse:
    output = await use_case.execute(
        CreateNotificationInput(**body.model_dump(), created_by=current_user.user_id)
    )
    return await _get_response(output.notification_id, query_service, current_user)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> NotificationResponse:
    return await _get_response(notification_id, query_service, current_user)


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def search_notifications(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[NotificationStatus] | None, Query(alias="status")] = None,
    priority: Annotated[list[NotificationPriority] | None, Query()] = None,
    recipient_user_id: UUID | None = None,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
) -> PaginatedResponse[NotificationResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over notifications — see
    `NotificationRepository.search`'s docstring for how `filters.q` is
    matched and for the `sort_order` default nuance."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SORT_FIELDS, default_field="created_at"
    )
    summaries, total = await query_service.search_notifications(
        organization_id=current_user.organization_id,
        query=filters.q,
        statuses=status_filter,
        priorities=priority,
        recipient_user_id=recipient_user_id,
        reference_type=reference_type,
        reference_id=reference_id,
        scheduled_from=scheduled_from,
        scheduled_to=scheduled_to,
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
    items = [NotificationResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


@router.get(
    "/recipient/{recipient_user_id}", response_model=PaginatedResponse[NotificationResponse]
)
async def list_notifications_for_recipient(
    recipient_user_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[NotificationResponse]:
    summaries = await query_service.list_notifications_for_recipient(recipient_user_id)
    items = [NotificationResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get(
    "/recipient/{recipient_user_id}/unread",
    response_model=PaginatedResponse[NotificationResponse],
)
async def list_unread_notifications_for_recipient(
    recipient_user_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[NotificationResponse]:
    summaries = await query_service.list_unread_notifications_for_recipient(recipient_user_id)
    items = [NotificationResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.patch("/{notification_id}/mark-sent", response_model=NotificationResponse)
async def mark_notification_sent(
    notification_id: UUID,
    use_case: MarkSentUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> NotificationResponse:
    await use_case.execute(MarkNotificationSentInput(notification_id=notification_id))
    return await _get_response(notification_id, query_service, current_user)


@router.patch("/{notification_id}/mark-delivered", response_model=NotificationResponse)
async def mark_notification_delivered(
    notification_id: UUID,
    use_case: MarkDeliveredUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> NotificationResponse:
    await use_case.execute(MarkNotificationDeliveredInput(notification_id=notification_id))
    return await _get_response(notification_id, query_service, current_user)


@router.patch("/{notification_id}/mark-read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    use_case: MarkReadUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> NotificationResponse:
    await use_case.execute(MarkNotificationReadInput(notification_id=notification_id))
    return await _get_response(notification_id, query_service, current_user)


@router.patch("/{notification_id}/cancel", response_model=NotificationResponse)
async def cancel_notification(
    notification_id: UUID,
    use_case: CancelUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> NotificationResponse:
    await use_case.execute(CancelNotificationInput(notification_id=notification_id))
    return await _get_response(notification_id, query_service, current_user)


@router.patch("/{notification_id}/expire", response_model=NotificationResponse)
async def expire_notification(
    notification_id: UUID,
    use_case: ExpireUseCase,
    query_service: QueryService,
    current_user: CurrentUser,
) -> NotificationResponse:
    await use_case.execute(ExpireNotificationInput(notification_id=notification_id))
    return await _get_response(notification_id, query_service, current_user)
