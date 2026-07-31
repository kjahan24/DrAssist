"""HTTP routes for the Audit Log module.

New — this module had no `api/` package before the REST APIs task (see
`container.py`'s scope note). Read-only: `GetById`/`ListForEntity`/
`ListForOrganization`/`ListForActor` only — no `POST`, since audit
entries are never directly client-created (see `api/schemas.py`'s own
docstring).

`list_for_entity`/`list_for_actor` take no `organization_id` parameter at
the query-service level (see that service's own docstring — `entity_id`/
`actor_user_id` alone are the natural keys for those two read axes), so
this router applies the tenant-isolation filter itself, defensively,
after fetching — the same multi-tenant-correctness posture
`ensure_same_organization` enforces everywhere else in this API, just
applied as a list filter here instead of a single-record guard.
`list_for_organization` never takes a client-supplied organization id at
all — it always uses `current_user.organization_id` directly, the same
"derive, don't trust" pattern `app.modules.authentication.api.router
.list_roles` already establishes for its own organization-scoped list.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.core.exceptions import NotFoundError
from app.modules.audit_log.api.dependencies import get_audit_log_query_service
from app.modules.audit_log.api.schemas import AuditLogResponse
from app.modules.audit_log.application.services.audit_log_query_service import (
    AuditLogQueryService,
)
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SORT_FIELDS = frozenset({"action", "source", "created_at", "entity_type"})

# `list_for_organization` accepts native offset/limit, but every other
# module's list endpoint fetches everything and paginates/sorts in
# memory via `paginate_and_sort` (see that helper's own docstring) — kept
# consistent here rather than special-casing the one query method that
# happens to support native pagination; this ceiling is a generous upper
# bound on how many entries one page-fetch pulls before in-memory slicing.
_FETCH_CEILING = 1000

QueryService = Annotated[AuditLogQueryService, Depends(get_audit_log_query_service)]


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
    current_user: CurrentUser,
) -> PaginatedResponse[AuditLogResponse]:
    summaries = await query_service.list_for_organization(
        current_user.organization_id, offset=0, limit=_FETCH_CEILING
    )
    items = [AuditLogResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
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
    summaries = await query_service.list_for_entity(entity_type=entity_type, entity_id=entity_id)
    own_org_summaries = [s for s in summaries if s.organization_id == current_user.organization_id]
    items = [AuditLogResponse.model_validate(s) for s in own_org_summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )


@router.get("/actor/{actor_user_id}", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs_for_actor(
    actor_user_id: UUID,
    query_service: QueryService,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[AuditLogResponse]:
    summaries = await query_service.list_for_actor(actor_user_id)
    own_org_summaries = [s for s in summaries if s.organization_id == current_user.organization_id]
    items = [AuditLogResponse.model_validate(s) for s in own_org_summaries]
    return paginate_and_sort(
        items, pagination=pagination, sorting=sorting, allowed_sort_fields=_SORT_FIELDS
    )
