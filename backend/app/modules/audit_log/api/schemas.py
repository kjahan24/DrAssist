"""Pydantic v2 response schema for the Audit Log module.

New — this module had no `api/` package before the REST APIs task (see
`container.py`'s scope note). Read-only: there is no request schema for
creating an entry, because there is no `POST` endpoint — "audit logs can
never be updated" and are never directly client-created either; entries
come only from `RecordAuditLog`, called internally by whichever module is
recording the event (see `container.py`'s own docstring on
`build_record_audit_log_use_case`).
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.schemas.base import ORJSONModel


class AuditLogResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    actor_user_id: UUID | None = None
    entity_type: str
    entity_id: UUID
    action: AuditAction
    source: AuditSource
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    created_at: datetime
