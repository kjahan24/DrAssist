"""Data Transfer Objects for the Audit Log module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (this task builds no HTTP endpoint — see `container.py`'s scope
note).

`RecordAuditLogInput` carries `organization_id` directly, unlike every
other module's own `Create<X>Input` (which derives `organization_id`
from a single parent). `actor_user_id` is nullable ("actor_user_id may
be null for system-generated events"), so there is no single reliable
parent to derive it from the way `Notification.organization_id` is
derived from its always-required `recipient_user_id` — the caller
(whichever module is recording the event) already knows the correct
`organization_id` from the entity being audited, and supplies it
directly. When `actor_user_id` *is* given,
`AuditLogConsistencyService.validate_actor_organization()` still checks
it against the supplied `organization_id`, so the value isn't blindly
trusted either.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.modules.audit_log.domain.enums import AuditAction, AuditSource

# --- RecordAuditLog ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordAuditLogInput:
    organization_id: UUID
    entity_type: str
    entity_id: UUID
    action: AuditAction
    source: AuditSource
    actor_user_id: UUID | None = None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RecordAuditLogOutput:
    audit_log_id: UUID
    created_at: datetime


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class AuditLogSummaryDTO:
    audit_log_id: UUID
    organization_id: UUID
    actor_user_id: UUID | None
    entity_type: str
    entity_id: UUID
    action: AuditAction
    source: AuditSource
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    correlation_id: str | None
    created_at: datetime

    @property
    def id(self) -> UUID:
        """Alias for `audit_log_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for
        the full reasoning (identical situation in every module)."""
        return self.audit_log_id
