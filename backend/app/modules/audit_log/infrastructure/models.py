"""SQLAlchemy ORM model for the Audit Log module.

One table: `audit_logs`. See `app.modules.audit_log.container` for the
module's scope note, and `docs/database/06_audit_and_activity.md` for
the architecture doc this table is built against.

**Deliberately does not use `TimestampMixin`/`SoftDeleteMixin`/
`AuditActorMixin`.** This task's own Entity field list has only
`created_at` — no `updated_at`, `deleted_at`, `created_by`, or
`updated_by` — and its Business Rules are explicit: "audit logs are
immutable", "can never be updated", "can never be deleted".
`docs/database/06_audit_and_activity.md` itself documents keeping those
four columns anyway "for schema consistency with every other table",
even though a trigger blocks them from ever being exercised; this
implementation follows this task's own narrower, explicit field list
instead (see rule 10 — build only what this task requires) and uses
`CreatedAtMixin` (added to `app.infrastructure.database.base` by this
task, purely additively) rather than carrying four columns nothing in
this codebase will ever populate or query.

**`organization_id` is `NOT NULL`, `ON DELETE RESTRICT`** — the doc's own
`audit_logs.organization_id` is nullable with `ON DELETE SET NULL` (to
capture platform-level events not tied to a tenant), but this task's
Business Rules state "every audit log belongs to one organization" with
no stated exception, and the Entity spec marks only `actor_user_id` as
nullable. A `NOT NULL` column cannot use `ON DELETE SET NULL` (violates
the constraint), so this reconciliation adopts `ON DELETE RESTRICT`
instead — the same treatment `docs/database/06_audit_and_activity.md`'s
own *other* table, `activity_logs`, already uses for its own `NOT NULL
organization_id`, and the same treatment every other module's own
`organization_id` column uses throughout this codebase.

**`actor_user_id`** is nullable, `ON DELETE SET NULL` — matching the
doc's `changed_by`/`user_id` treatment on both of its own tables:
historical attribution survives even if the acting user account is
later hard-deleted, the same reasoning
`app.infrastructure.database.base.AuditActorMixin` already documents for
`created_by`/`updated_by`.

**`entity_id` carries no foreign key** — a polymorphic pointer whose
target table varies by `entity_type` (free-form text, not a closed
enum): "by design this table must be able to reference *any* table,
including ones added after `audit_logs` itself was created" (the doc's
own words) — see `domain/entities.py` for the full reasoning.

**True immutability is enforced by a database trigger**, not just
omitting `update()`/`delete()` from the repository (see
`domain/repositories.py`): the Alembic migration installs
`reject_mutation()` (shared, reusable function — see the migration's own
docstring) via `trg_audit_logs_immutable`, exactly as
`docs/database/06_audit_and_activity.md` specifies. This guarantees
immutability even against a compromised or misconfigured application
role, not just disciplined application code — the doc's own stated
rationale, and squarely what rule 13's "security, auditability,
healthcare compliance" review asks for.

Indexes mirror `docs/database/06_audit_and_activity.md`'s own strategy,
generalized for this task's merged `entity_type`/`entity_id` (replacing
the doc's separate `table_name`/`record_id` and `resource_type`/
`resource_id` columns from its two source tables — see
`application/services/audit_log_query_service.py`'s docstring for the
three read axes these back): `(entity_type, entity_id, created_at DESC)`
— "show me the history of this row"; `(organization_id, created_at DESC)`
— an organization-wide activity feed; `(actor_user_id, created_at DESC)`
— "show this user's activity"; a BRIN index on `created_at` for cheap
retention-window scans at very high volume, the doc's own recommendation
for this exact table shape; and `correlation_id`, new in this task (not
in the doc), for tracing a single multi-step operation across rows.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, pg_enum
from app.modules.audit_log.domain.enums import AuditAction, AuditSource

_audit_action_enum = pg_enum(AuditAction, "audit_action_enum")
_audit_source_enum = pg_enum(AuditSource, "audit_source_enum")


class AuditLogModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    action: Mapped[AuditAction] = mapped_column(_audit_action_enum, nullable=False)
    source: Mapped[AuditSource] = mapped_column(_audit_source_enum, nullable=False)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    ip_address: Mapped[str | None] = mapped_column(INET, default=None)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    request_id: Mapped[str | None] = mapped_column(Text, default=None)
    correlation_id: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "ix_audit_logs_entity_type_entity_id",
            "entity_type",
            "entity_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_audit_logs_organization_id_created_at",
            "organization_id",
            text("created_at DESC"),
        ),
        Index("ix_audit_logs_actor_user_id_created_at", "actor_user_id", text("created_at DESC")),
        Index("ix_audit_logs_correlation_id", "correlation_id"),
        Index("ix_audit_logs_created_at_brin", "created_at", postgresql_using="brin"),
    )
