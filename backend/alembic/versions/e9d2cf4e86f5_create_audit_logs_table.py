"""create audit logs table

Creates the Audit Log module's foundation schema: `audit_logs`, plus the
shared `reject_mutation()` trigger function `docs/database
/06_audit_and_activity.md` defines for every compliance-critical,
append-only table in this schema (`audit_logs`, `activity_logs`,
`auth_login_attempts`, `conversation_transcripts`,
`patient_timeline_events`) — none of those other tables exist in this
codebase yet, so this migration creates the function and applies it only
to `audit_logs`; a future migration building one of those other tables
is expected to reuse this same function (`CREATE OR REPLACE FUNCTION` is
idempotent) rather than duplicate it.

Reconciles this task's own explicit field list against
`docs/database/06_audit_and_activity.md`'s own `audit_logs` design in two
places — see `app.modules.audit_log.infrastructure.models`'s module
docstring for the full reasoning:

1. `organization_id` is `NOT NULL` / `ON DELETE RESTRICT` here (the doc's
   own version is nullable / `ON DELETE SET NULL`) — this task's Business
   Rules state "every audit log belongs to one organization" with no
   exception, and only `actor_user_id` is marked nullable in the Entity
   spec.
2. No `updated_at`/`deleted_at`/`created_by`/`updated_by` columns (the
   doc keeps them "for schema consistency", trigger-blocked from ever
   changing) — this task's own field list has only `created_at`.

`actor_user_id` carries no `NOT NULL` (nullable, "actor_user_id may be
null for system-generated events") and `ON DELETE SET NULL`, matching
the doc's own `changed_by`/`user_id` treatment. `entity_id` carries no
foreign key — a polymorphic pointer whose target table varies by
`entity_type` — "by design this table must be able to reference *any*
table, including ones added after `audit_logs` itself was created" (the
doc's own words).

Indexes and the immutability trigger match
`docs/database/06_audit_and_activity.md`'s own recommendation for this
table shape, generalized for this task's merged `entity_type`/
`entity_id` columns (see `infrastructure/models.py` for the full
reasoning): a composite index per read axis (`(entity_type, entity_id,
created_at DESC)`, `(organization_id, created_at DESC)`,
`(actor_user_id, created_at DESC)`), a BRIN index on `created_at` for
cheap retention-window scans at very high volume, and
`trg_audit_logs_immutable` (`BEFORE UPDATE OR DELETE`) rejecting any
mutation at the database level — enforced even against a compromised or
misconfigured application role, not just disciplined application code.

Revision ID: e9d2cf4e86f5
Revises: b22ab71b3d39
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e9d2cf4e86f5"
down_revision: str | None = "b22ab71b3d39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    audit_action_enum = postgresql.ENUM(
        "create",
        "update",
        "delete",
        "soft_delete",
        "restore",
        "approve",
        "reject",
        "login",
        "logout",
        "export",
        "view",
        name="audit_action_enum",
        create_type=False,
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    audit_source_enum = postgresql.ENUM(
        "api",
        "system",
        "ai",
        "background_job",
        name="audit_source_enum",
        create_type=False,
    )
    audit_source_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("source", audit_source_enum, nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_audit_logs_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_audit_logs_actor_user_id_users",
            ondelete="SET NULL",
        ),
    )

    op.execute(
        "CREATE INDEX ix_audit_logs_entity_type_entity_id "
        "ON audit_logs (entity_type, entity_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_organization_id_created_at "
        "ON audit_logs (organization_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_actor_user_id_created_at "
        "ON audit_logs (actor_user_id, created_at DESC)"
    )
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])
    op.execute("CREATE INDEX ix_audit_logs_created_at_brin ON audit_logs USING BRIN (created_at)")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: % is not permitted on this table',
                TG_TABLE_NAME, TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_immutable
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION reject_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS reject_mutation()")

    op.drop_table("audit_logs")

    postgresql.ENUM(name="audit_source_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="audit_action_enum").drop(op.get_bind(), checkfirst=True)
