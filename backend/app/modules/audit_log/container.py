"""Module composition root.

Same shape as `app.modules.notification.container` for the same reason:
this task explicitly excludes API endpoints ("Do NOT implement API
endpoints"), so there is no `api/` package and therefore nowhere else to
put the write-side wiring. `container.py` builds both here:
`build_audit_log_facade` (the read-only public port, matching every
prior module exactly) and `build_record_audit_log_use_case` (bound to a
`SqlAlchemyUnitOfWork` for that same session), for a future caller —
Audit middleware, an Event Bus subscriber, or a Background Job (all
explicitly out of scope for this task; see the Future Compatibility list
below) — to invoke directly, the same way `app.modules.appointment.api
.dependencies` calls `app.modules.appointment.container
.build_appointment_facade` today.

Scope note — this task builds the Audit Log module's **foundation**
only: the `AuditLog` entity (`domain/entities.py` — extends `Entity`,
not `AggregateRoot`; see that file's own docstring for why), its
insert-only repository (`domain/repositories.py`), `RecordAuditLog`
(validates the actor's organization via `AuditLogConsistencyService`
when an actor is given — see that service's own docstring for why
`organization_id` is supplied directly rather than derived), and the
public read-only query facade. True immutability — "audit logs can never
be updated", "can never be deleted" — is enforced at three independent
layers: the repository interface declares no `update()`/`delete()` at
all; the concrete repository's `add()` is insert-only and raises if a
row with the same id already exists; and the Alembic migration installs
a database trigger (`reject_mutation()` / `trg_audit_logs_immutable`,
per `docs/database/06_audit_and_activity.md`) that rejects `UPDATE`/
`DELETE` at the database level regardless of what application code does.

A latent, pre-existing issue was discovered (not fixed) while building
this module's own integration tests against a real PostgreSQL instance:
`app.modules.authentication.infrastructure.models.UserSessionModel
.ip_address` — the only other `INET` column in this codebase — is typed
`str | None` on its domain entity but, like this module's own
`AuditLogModel.ip_address`, asyncpg actually deserializes it into an
`ipaddress.IPv4Address`/`IPv6Address` object; `UserSessionModel` has no
integration test exercising a round trip, so this was never caught. See
`infrastructure/mappers.py` for how this module's own mapper coerces it
to `str`. Reported here rather than fixed, per rule 1/12 — modifying the
Authentication module is out of this task's own scope.

This module deliberately does **not** implement API endpoints, frontend,
authentication, authorization middleware, or any Background Job (per
this task's explicit exclusions), and does not modify the Authentication,
Organization, Doctor, Patient, Appointment, Schedule, Visit, Clinical
Notes, SOAP Notes, Lab Orders, Lab Results, Prescription, Notification,
or RBAC modules or their tables — it only *reads* Authentication through
its public port (`UserQueryPort`), to validate an optional actor's
organization when one is given.

Audit middleware, Event Bus wiring, Background Jobs, Notification
integration, Security Monitoring, SIEM, FHIR `AuditEvent`, AI activity
logging, Family/Caregiver Access, and Medical Community moderation logs
are explicitly out of scope for this task — they are expected to become
their own integrations, each depending on `AuditLogQueryPort` (keyed by
`audit_log_id`, or `list_for_entity`/`list_for_organization`/
`list_for_actor` for the three read axes
`application/services/audit_log_query_service.py` documents) or calling
`build_record_audit_log_use_case` directly to write new entries, the
same way this module itself depends on Authentication's own port.
Nothing about this schema needs to change to support them: `source`
already distinguishes API/System/AI/BackgroundJob-originated entries for
a future SIEM or AI-activity consumer, and `request_id`/`correlation_id`
already give a future distributed-tracing integration what it needs
without a schema change.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import get_event_bus
from app.modules.audit_log.application.services.audit_log_consistency_service import (
    AuditLogConsistencyService,
)
from app.modules.audit_log.application.services.audit_log_query_service import (
    AuditLogQueryService,
)
from app.modules.audit_log.application.use_cases.record_audit_log import RecordAuditLog
from app.modules.audit_log.infrastructure.repositories import SqlAlchemyAuditLogRepository
from app.modules.audit_log.public.facade import AuditLogFacade
from app.modules.authentication.container import build_authentication_facade
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def build_audit_log_facade(session: AsyncSession) -> AuditLogFacade:
    """Construct an `AuditLogFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    audit_log_repository = SqlAlchemyAuditLogRepository(session)
    query_service = AuditLogQueryService(audit_log_repository=audit_log_repository)
    return AuditLogFacade(query_service=query_service)


def build_record_audit_log_use_case(session: AsyncSession) -> RecordAuditLog:
    audit_log_repository = SqlAlchemyAuditLogRepository(session)
    consistency_service = AuditLogConsistencyService(
        user_query_port=build_authentication_facade(session)
    )
    unit_of_work = SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())
    return RecordAuditLog(
        audit_log_repository=audit_log_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )
