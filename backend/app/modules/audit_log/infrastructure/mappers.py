"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.

`model.ip_address` is coerced to `str` on the way out — confirmed
against a real PostgreSQL instance while building this module: asyncpg
deserializes an `INET` column into an `ipaddress.IPv4Address`/
`IPv6Address` object, not a plain `str`, so reading it back without
converting would violate `AuditLog.ip_address`'s own `str | None` type
(this codebase's other `INET` column,
`app.modules.authentication.infrastructure.models.UserSessionModel
.ip_address`, appears to share this same latent mismatch — it has no
integration test exercising a round trip, so it was never caught; not
fixed here, out of this task's own scope, see `container.py`'s scope
note).

There is deliberately no `apply_audit_log_to_model()` counterpart to
every other module's own `apply_<x>_to_model()` — that function exists
elsewhere to let a repository's `add()` overwrite an existing row's
columns from an updated in-memory entity, which `AuditLogRepository.add()`
never does (see its own docstring). `audit_log_to_model()` below only
ever builds a brand-new `AuditLogModel` for a brand-new insert.
"""

from app.modules.audit_log.domain.entities import AuditLog
from app.modules.audit_log.infrastructure.models import AuditLogModel


def audit_log_to_domain(model: AuditLogModel) -> AuditLog:
    return AuditLog(
        id=model.id,
        organization_id=model.organization_id,
        actor_user_id=model.actor_user_id,
        entity_type=model.entity_type,
        entity_id=model.entity_id,
        action=model.action,
        source=model.source,
        old_values=model.old_values,
        new_values=model.new_values,
        ip_address=str(model.ip_address) if model.ip_address is not None else None,
        user_agent=model.user_agent,
        request_id=model.request_id,
        correlation_id=model.correlation_id,
        created_at=model.created_at,
    )


def audit_log_to_model(entity: AuditLog) -> AuditLogModel:
    return AuditLogModel(
        id=entity.id,
        organization_id=entity.organization_id,
        actor_user_id=entity.actor_user_id,
        entity_type=entity.entity_type,
        entity_id=entity.entity_id,
        action=entity.action,
        source=entity.source,
        old_values=entity.old_values,
        new_values=entity.new_values,
        ip_address=entity.ip_address,
        user_agent=entity.user_agent,
        request_id=entity.request_id,
        correlation_id=entity.correlation_id,
    )
