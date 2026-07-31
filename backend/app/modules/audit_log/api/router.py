"""HTTP routes for the Audit Log module.

New — this module had no `api/` package before the REST APIs task (see
`container.py`'s scope note). Read-only: `GetById`/`ListForEntity`/
`ListForOrganization`/`ListForActor` only — no `POST`, since audit
entries are never directly client-created (see `api/schemas.py`'s own
docstring).

Search & Filtering module: all three list endpoints below now go through
`AuditLogQueryService.search`, which filters by `organization_id` at the
SQL layer — replacing the REST APIs task's original approach (documented
in the git history this docstring used to carry) of fetching up to 1000
rows per request and paginating/filtering in memory, including a
defensive post-fetch organization filter on the entity/actor endpoints.
`search` takes `organization_id` as a required, non-optional parameter,
so that cross-tenant filtering is structural rather than a filter someone
could forget to apply — the same "derive, don't trust" posture
`app.modules.authentication.api.router.list_roles` already establishes,
now extended to these two endpoints as well as the organization-wide one.
"""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.audit_log.api.dependencies import get_audit_log_query_service
from app.modules.audit_log.api.schemas import AuditLogResponse
from app.modules.audit_log.application.services.audit_log_query_service import (
    AuditLogQueryService,
)
from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.schemas.base import PaginatedResponse

_SORT_FIELDS = frozenset({"action", "source", "created_at", "entity_type"})

router = APIRouter()

QueryService = Annotated[AuditLogQueryService, Depends(get_audit_log_query_service)]


def _effective_sort_order(sorting: Sorting) -> Literal["asc", "desc"]:
    """Every pre-existing `list_for_*` repository method here orders
    `created_at.desc()` with no way to ask for anything else, and every
    pre-existing endpoint preserved that when the caller didn't specify a
    `sort_by` (`paginate_and_sort` skips sorting entirely when `sort_by`
    is `None`, leaving the repository's own fetch order intact). Now that
    `search()` always applies an explicit `ORDER BY`, forwarding
    `sorting.sort_order` unconditionally would silently flip the default
    from newest-first to oldest-first, since `SortParams.sort_order`
    itself defaults to `"asc"` — a real behavior regression for existing
    callers relying on the old default. Falling back to `"desc"` only
    when `sort_by` was never given preserves the old default exactly,
    while still letting a caller who *does* pick a `sort_by` also pick
    its direction, same as every other module."""
    if sorting.sort_by is None:
        return "desc"
    return sorting.sort_order


@router.get("/{audit_log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_log_id: UUID, query_service: QueryService, current_user: CurrentUser
) -> AuditLogResponse:
    summary = await query_service.get_by_id(audit_log_id)
    if summary is None:
        raise NotFoundError(f"no audit log found with id {audit_log_id}")
    response = AuditLogResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs_for_organization(
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    action: Annotated[list[AuditAction] | None, Query()] = None,
    source: Annotated[list[AuditSource] | None, Query()] = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    correlation_id: str | None = None,
) -> PaginatedResponse[AuditLogResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate — see `AuditLogRepository.search`'s
    docstring for how `filters.q` is matched. `filters.created_from`/
    `_to` are the only date-range filters accepted (audit logs have no
    `updated_at`); `filters.include_deleted` has no effect here (audit
    logs cannot be deleted at all) and is accepted only because it's part
    of the shared `SearchFilters` dependency every module reuses."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SORT_FIELDS, default_field="created_at"
    )
    summaries, total = await query_service.search(
        organization_id=current_user.organization_id,
        query=filters.q,
        actions=action,
        sources=source,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        correlation_id=correlation_id,
        created_from=filters.created_from,
        created_to=filters.created_to,
        sort_by=sort_field,
        sort_order=_effective_sort_order(sorting),
        offset=pagination.offset,
        limit=pagination.limit,
    )
    items = [AuditLogResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs_for_entity(
    entity_type: str,
    entity_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[AuditLogResponse]:
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SORT_FIELDS, default_field="created_at"
    )
    summaries, total = await query_service.search(
        organization_id=current_user.organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        sort_by=sort_field,
        sort_order=_effective_sort_order(sorting),
        offset=pagination.offset,
        limit=pagination.limit,
    )
    items = [AuditLogResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


@router.get("/actor/{actor_user_id}", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs_for_actor(
    actor_user_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[AuditLogResponse]:
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SORT_FIELDS, default_field="created_at"
    )
    summaries, total = await query_service.search(
        organization_id=current_user.organization_id,
        actor_user_id=actor_user_id,
        sort_by=sort_field,
        sort_order=_effective_sort_order(sorting),
        offset=pagination.offset,
        limit=pagination.limit,
    )
    items = [AuditLogResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )
