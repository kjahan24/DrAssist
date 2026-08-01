"""Audit Log module entity: `AuditLog`.

**Extends `Entity`, not `AggregateRoot`.** Every other module's aggregate
root in this codebase is an `AggregateRoot` — it has `updated_at`,
records domain events via `record_event()`, and its lifecycle continues
after creation (named methods mutate it further). `AuditLog` has none of
that: "Audit logs are immutable", "can never be updated", "can never be
deleted" — there is no method on this class beyond `__post_init__` and
the `record()` factory, and no `updated_at` at all (only `created_at`,
via `app.infrastructure.database.base.CreatedAtMixin` at the ORM layer —
see `infrastructure/models.py`). Using `AggregateRoot` here would add an
`updated_at` field and an event-recording surface this entity has no use
for and that would misleadingly suggest it can change after creation.
No domain event is recorded on `record()` either: `AuditLog` itself
*is* the record of something that already happened — an event announcing
"an audit log was recorded" would be redundant, and `container.py`'s
scope note explains why Event Bus integration is deliberately not wired
up by this task.

`organization_id` is **not** nullable, unlike
`docs/database/06_audit_and_activity.md`'s own `audit_logs.organization_id`
(nullable there, to capture platform-level events not tied to a single
tenant). This task's own Business Rules are unambiguous — "Every audit
log belongs to one organization" states no exception, and the Entity
spec marks only `actor_user_id` as nullable — so that rule governs this
implementation; see `infrastructure/models.py` for the resulting FK
`ON DELETE` reconciliation this required.

`entity_type` is a plain, free-form string, not a closed enum — the same
"no closed set of valid values was specified, and this module must be
able to reference *any* entity across nearly every other module,
including ones that don't exist yet" reasoning
`app.modules.notification.domain.entities.Notification.reference_type`
already establishes for the identical shape, now stated explicitly by
`docs/database/06_audit_and_activity.md` itself: "by design this table
must be able to reference *any* table, including ones added after
`audit_logs` itself was created." `entity_id` therefore carries no
foreign key either, for the same reason.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.modules.audit_log.domain.enums import AuditAction, AuditSource
from app.modules.audit_log.domain.exceptions import EntityTypeRequiredError
from app.shared.domain.entity import Entity


@dataclass(kw_only=True, eq=False)
class AuditLog(Entity):
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
    # Not the persisted source of truth: `infrastructure.mappers
    # .audit_log_to_model()` does not map this value onto `AuditLogModel`,
    # which relies on `CreatedAtMixin`'s `server_default=func.now()`
    # instead (see `infrastructure/models.py`). This in-memory default
    # exists only so a freshly `record()`-ed, not-yet-persisted entity has
    # a usable value; a round-trip through the repository always
    # overwrites it with the database-generated timestamp.
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.entity_type or not self.entity_type.strip():
            raise EntityTypeRequiredError()
        self.entity_type = self.entity_type.strip()

    @classmethod
    def record(
        cls,
        *,
        organization_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: AuditAction,
        source: AuditSource,
        actor_user_id: UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> "AuditLog":
        """Named `record()`, not `create()` — this module's own
        `AuditAction.CREATE` member would make `AuditLog.create()` read as
        "record a Create action" specifically, when this factory is used
        for every action type."""
        return cls(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            source=source,
            actor_user_id=actor_user_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            correlation_id=correlation_id,
        )
