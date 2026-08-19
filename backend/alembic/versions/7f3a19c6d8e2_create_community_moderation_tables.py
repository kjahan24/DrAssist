"""create community moderation tables

Phase 5.9 — Community Moderation & Trust/Safety module: creates four
tables — `community_reports`, `moderation_actions`,
`moderation_restrictions`, `doctor_verifications` — this task's own
DATABASE section names all four as distinct tables.

`community_reports.target_id`/`moderation_actions.target_id` have
deliberately no foreign key — a single column cannot reference
`community_posts`/`community_questions`/`community_answers`/
`community_comments`/`communities`/`users` conditionally at the schema
level, the same "polymorphic reference, validated at write time through
each peer module's own public query port instead" pattern
`app.modules.community_engagement.infrastructure.models` already
establishes for `votes.target_id`/`saved_content.target_id`. There is no
separate `reported_user_id` column either — for a `USER`-targeted report,
`target_id` *is* the reported user's id; `(target_type, target_id)` is
what every index below is built around, so `WHERE target_type = 'user'
AND target_id = :user_id` already serves this task's own literal "index
for ... reported_user_id" requirement without a redundant second column.

`community_reports` carries a partial unique index —
`(reporter_id, target_type, target_id) WHERE status IN ('open',
'under_review')` — backing "Prevent duplicate reports" as a concurrency
safety net under `DuplicateOpenReportError`'s own application-level
check, the same "DB constraint under application-level coordination"
pattern `app.modules.community_answers.infrastructure.models
.CommunityAnswerModel`'s own `uq_community_answers_question_id_best`
partial index already establishes.

`doctor_verifications.doctor_id` is uniquely constrained — one
verification row per doctor; `DoctorVerification.resubmit()` transitions
the same row back to `PENDING` rather than inserting a new one.

`moderation_actions` has `created_at` only (no `updated_at`) — it is
never mutated after insert, mirroring `audit_logs`' identical shape (see
`app.modules.audit_log.infrastructure.models`). `moderation_restrictions`
also has `created_at` only, despite `ModerationRestriction` being an
aggregate root, for the same "never mutated after `issue()`" reason — see
`app.modules.community_moderation.domain.entities`'s own module
docstring.

No existing table (from any prior phase) is altered by this migration —
four wholly new tables only.

Revision ID: 7f3a19c6d8e2
Revises: 2be7bd77eb69
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7f3a19c6d8e2"
down_revision: str | None = "2be7bd77eb69"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    moderation_target_type_enum = postgresql.ENUM(
        "post",
        "question",
        "answer",
        "comment",
        "community",
        "user",
        name="moderation_target_type_enum",
        create_type=False,
    )
    moderation_target_type_enum.create(op.get_bind(), checkfirst=True)

    report_reason_enum = postgresql.ENUM(
        "medical_misinformation",
        "spam",
        "harassment",
        "abuse",
        "hate_discrimination",
        "privacy_violation",
        "impersonation",
        "dangerous_medical_advice",
        "self_harm_concern",
        "illegal_content",
        "other",
        name="report_reason_enum",
        create_type=False,
    )
    report_reason_enum.create(op.get_bind(), checkfirst=True)

    report_status_enum = postgresql.ENUM(
        "open", "under_review", "resolved", "rejected", name="report_status_enum", create_type=False
    )
    report_status_enum.create(op.get_bind(), checkfirst=True)

    report_priority_enum = postgresql.ENUM(
        "low", "medium", "high", "critical", name="report_priority_enum", create_type=False
    )
    report_priority_enum.create(op.get_bind(), checkfirst=True)

    moderation_action_type_enum = postgresql.ENUM(
        "approve",
        "remove",
        "restrict",
        "lock",
        "restore",
        "warn_user",
        "restrict_user",
        "suspend_user",
        "ban_user",
        name="moderation_action_type_enum",
        create_type=False,
    )
    moderation_action_type_enum.create(op.get_bind(), checkfirst=True)

    verification_status_enum = postgresql.ENUM(
        "pending",
        "verified",
        "rejected",
        "revoked",
        name="verification_status_enum",
        create_type=False,
    )
    verification_status_enum.create(op.get_bind(), checkfirst=True)

    moderation_restriction_type_enum = postgresql.ENUM(
        "warning",
        "temporary_restriction",
        "suspension",
        "permanent_ban",
        name="moderation_restriction_type_enum",
        create_type=False,
    )
    moderation_restriction_type_enum.create(op.get_bind(), checkfirst=True)

    # --- community_reports -------------------------------------------------------
    op.create_table(
        "community_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", moderation_target_type_enum, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", report_reason_enum, nullable=False),
        sa.Column("status", report_status_enum, nullable=False, server_default="open"),
        sa.Column("priority", report_priority_enum, nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("assigned_moderator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("moderator_note", sa.String(), nullable=True),
        sa.Column("resolution", sa.String(), nullable=True),
        sa.Column("resolved_at", _TIMESTAMPTZ, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_community_reports"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_community_reports_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_reports_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name="fk_community_reports_reporter_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_moderator_id"],
            ["users.id"],
            name="fk_community_reports_assigned_moderator_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "uq_community_reports_reporter_target_open",
        "community_reports",
        ["reporter_id", "target_type", "target_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'under_review')"),
    )
    op.create_index(
        "ix_community_reports_organization_id", "community_reports", ["organization_id"]
    )
    op.create_index("ix_community_reports_community_id", "community_reports", ["community_id"])
    op.create_index("ix_community_reports_reporter_id", "community_reports", ["reporter_id"])
    op.create_index("ix_community_reports_target_type", "community_reports", ["target_type"])
    op.create_index("ix_community_reports_target_id", "community_reports", ["target_id"])
    op.create_index("ix_community_reports_status", "community_reports", ["status"])
    op.create_index("ix_community_reports_priority", "community_reports", ["priority"])
    op.create_index(
        "ix_community_reports_assigned_moderator_id",
        "community_reports",
        ["assigned_moderator_id"],
    )
    op.create_index("ix_community_reports_created_at", "community_reports", ["created_at"])

    # --- moderation_actions -------------------------------------------------------
    op.create_table(
        "moderation_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", moderation_action_type_enum, nullable=False),
        sa.Column("target_type", moderation_target_type_enum, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("moderator_note", sa.String(), nullable=True),
        sa.Column("previous_state", sa.String(), nullable=True),
        sa.Column("new_state", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_moderation_actions"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_moderation_actions_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_moderation_actions_actor_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["community_reports.id"],
            name="fk_moderation_actions_report_id_community_reports",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_moderation_actions_organization_id", "moderation_actions", ["organization_id"]
    )
    op.create_index("ix_moderation_actions_actor_id", "moderation_actions", ["actor_id"])
    op.create_index("ix_moderation_actions_target_type", "moderation_actions", ["target_type"])
    op.create_index("ix_moderation_actions_target_id", "moderation_actions", ["target_id"])
    op.create_index(
        "ix_moderation_actions_target_type_target_id",
        "moderation_actions",
        ["target_type", "target_id"],
    )
    op.create_index("ix_moderation_actions_report_id", "moderation_actions", ["report_id"])
    op.create_index("ix_moderation_actions_created_at", "moderation_actions", ["created_at"])

    # --- moderation_restrictions ----------------------------------------------------
    op.create_table(
        "moderation_restrictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restriction_type", moderation_restriction_type_enum, nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("starts_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("ends_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_moderation_restrictions"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_moderation_restrictions_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_moderation_restrictions_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_moderation_restrictions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"],
            ["users.id"],
            name="fk_moderation_restrictions_issued_by_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["community_reports.id"],
            name="fk_moderation_restrictions_report_id_community_reports",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_moderation_restrictions_organization_id",
        "moderation_restrictions",
        ["organization_id"],
    )
    op.create_index(
        "ix_moderation_restrictions_community_id", "moderation_restrictions", ["community_id"]
    )
    op.create_index("ix_moderation_restrictions_user_id", "moderation_restrictions", ["user_id"])
    op.create_index(
        "ix_moderation_restrictions_user_community",
        "moderation_restrictions",
        ["user_id", "community_id"],
    )
    op.create_index(
        "ix_moderation_restrictions_report_id", "moderation_restrictions", ["report_id"]
    )
    op.create_index(
        "ix_moderation_restrictions_created_at", "moderation_restrictions", ["created_at"]
    )

    # --- doctor_verifications -----------------------------------------------------
    op.create_table(
        "doctor_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", verification_status_enum, nullable=False, server_default="pending"),
        sa.Column("specialty", sa.String(), nullable=True),
        sa.Column("verifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("revocation_reason", sa.String(), nullable=True),
        sa.Column(
            "verification_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_verifications"),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_verifications_doctor_id_doctors",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_doctor_verifications_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_doctor_verifications_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verifier_id"],
            ["users.id"],
            name="fk_doctor_verifications_verifier_id_users",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("doctor_id", name="uq_doctor_verifications_doctor_id"),
    )
    op.create_index("ix_doctor_verifications_user_id", "doctor_verifications", ["user_id"])
    op.create_index(
        "ix_doctor_verifications_organization_id", "doctor_verifications", ["organization_id"]
    )
    op.create_index("ix_doctor_verifications_status", "doctor_verifications", ["status"])


def downgrade() -> None:
    op.drop_table("doctor_verifications")
    op.drop_table("moderation_restrictions")
    op.drop_table("moderation_actions")
    op.drop_table("community_reports")

    postgresql.ENUM(name="moderation_restriction_type_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="verification_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="moderation_action_type_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="report_priority_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="report_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="report_reason_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="moderation_target_type_enum").drop(op.get_bind(), checkfirst=True)
