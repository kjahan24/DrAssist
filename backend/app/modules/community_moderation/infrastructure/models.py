"""SQLAlchemy ORM models for the Community Moderation module.

Four tables: `community_reports`, `moderation_actions`,
`moderation_restrictions`, `doctor_verifications` — matching this task's
own DATABASE section literally.

`target_id` on `community_reports` and `moderation_actions` has
deliberately no foreign key — a single column cannot reference
`community_posts`/`community_questions`/`community_answers`/
`community_comments`/`communities`/`users` conditionally at the schema
level. Existence/tenant validation happens once, at write time, through
each peer module's own public query port instead — see
`_target_resolution.py`'s own docstring. There is also no separate
`reported_user_id` column: for a `USER`-targeted report, `target_id` *is*
the reported user's id — `(target_type, target_id)` is what every index
below is built around, so `WHERE target_type = 'user' AND target_id =
:user_id` already serves the "index on ... reported_user_id" DATABASE
requirement without a second, redundant column.

`ModerationActionModel` uses `CreatedAtMixin` only (no `updated_at`) —
`ModerationAction` is an `Entity`, not an `AggregateRoot`; it is never
mutated after creation, mirroring `AuditLogModel`'s identical shape (see
`app.modules.audit_log.infrastructure.models`). `ModerationRestrictionModel`
also uses `CreatedAtMixin` only, despite `ModerationRestriction` being an
`AggregateRoot` (which always carries an in-memory `updated_at`) — it has
no mutation method beyond `issue()` either, so nothing is ever touched
after the initial insert; `infrastructure/mappers.py` synthesizes
`updated_at=model.created_at` on load, the same "no mutation, no real
column" choice `app.modules.community_engagement.infrastructure.models`
already made for `SavedContentModel`/`TopicFollowerModel`/etc.
`CommunityReportModel`/`DoctorVerificationModel` use `TimestampMixin`
(real `updated_at`) since both aggregates genuinely are mutated in place
(`assign`/`resolve`/`reject`/`set_priority`; `approve`/`reject`/`revoke`/
`resubmit`).

`community_reports` carries a partial unique index —
`(reporter_id, target_type, target_id) WHERE status IN ('open',
'under_review')` — backing "Prevent duplicate reports": a reporter may
have at most one *currently open* report against a given target, but may
file a new one after a prior report is resolved/rejected. The same
"partial unique index as a concurrency safety net under
`DuplicateOpenReportError`'s own application-level check" pattern
`app.modules.community_answers.infrastructure.models.CommunityAnswerModel`
's own `uq_community_answers_question_id_best` already establishes.

`doctor_verifications.doctor_id` is uniquely constrained — one verification
row per doctor (see `DoctorVerification`'s own module docstring for the
request/resubmit lifecycle that keeps it that way rather than accumulating
a new row per request).
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationRestrictionType,
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
    VerificationStatus,
)

_moderation_target_type_enum = pg_enum(ModerationTargetType, "moderation_target_type_enum")
_report_reason_enum = pg_enum(ReportReason, "report_reason_enum")
_report_status_enum = pg_enum(ReportStatus, "report_status_enum")
_report_priority_enum = pg_enum(ReportPriority, "report_priority_enum")
_moderation_action_type_enum = pg_enum(ModerationActionType, "moderation_action_type_enum")
_verification_status_enum = pg_enum(VerificationStatus, "verification_status_enum")
_moderation_restriction_type_enum = pg_enum(
    ModerationRestrictionType, "moderation_restriction_type_enum"
)


class CommunityReportModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_reports"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[ModerationTargetType] = mapped_column(
        _moderation_target_type_enum, nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason: Mapped[ReportReason] = mapped_column(_report_reason_enum, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        _report_status_enum, nullable=False, default=ReportStatus.OPEN
    )
    priority: Mapped[ReportPriority] = mapped_column(_report_priority_enum, nullable=False)
    description: Mapped[str | None] = mapped_column(default=None)
    assigned_moderator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    moderator_note: Mapped[str | None] = mapped_column(default=None)
    resolution: Mapped[str | None] = mapped_column(default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_community_reports_reporter_target_open",
            "reporter_id",
            "target_type",
            "target_id",
            unique=True,
            postgresql_where="status IN ('open', 'under_review')",
        ),
        Index("ix_community_reports_organization_id", "organization_id"),
        Index("ix_community_reports_community_id", "community_id"),
        Index("ix_community_reports_reporter_id", "reporter_id"),
        Index("ix_community_reports_target_type", "target_type"),
        Index("ix_community_reports_target_id", "target_id"),
        Index("ix_community_reports_status", "status"),
        Index("ix_community_reports_priority", "priority"),
        Index("ix_community_reports_assigned_moderator_id", "assigned_moderator_id"),
        Index("ix_community_reports_created_at", "created_at"),
    )


class ModerationActionModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "moderation_actions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[ModerationActionType] = mapped_column(
        _moderation_action_type_enum, nullable=False
    )
    target_type: Mapped[ModerationTargetType] = mapped_column(
        _moderation_target_type_enum, nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(nullable=False)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_reports.id", ondelete="SET NULL"), default=None
    )
    moderator_note: Mapped[str | None] = mapped_column(default=None)
    previous_state: Mapped[str | None] = mapped_column(default=None)
    new_state: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (
        Index("ix_moderation_actions_organization_id", "organization_id"),
        Index("ix_moderation_actions_actor_id", "actor_id"),
        Index("ix_moderation_actions_target_type", "target_type"),
        Index("ix_moderation_actions_target_id", "target_id"),
        Index("ix_moderation_actions_target_type_target_id", "target_type", "target_id"),
        Index("ix_moderation_actions_report_id", "report_id"),
        Index("ix_moderation_actions_created_at", "created_at"),
    )


class ModerationRestrictionModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "moderation_restrictions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    issued_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    restriction_type: Mapped[ModerationRestrictionType] = mapped_column(
        _moderation_restriction_type_enum, nullable=False
    )
    reason: Mapped[str] = mapped_column(nullable=False)
    starts_at: Mapped[datetime] = mapped_column(nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(default=None)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_reports.id", ondelete="SET NULL"), default=None
    )

    __table_args__ = (
        Index("ix_moderation_restrictions_organization_id", "organization_id"),
        Index("ix_moderation_restrictions_community_id", "community_id"),
        Index("ix_moderation_restrictions_user_id", "user_id"),
        Index("ix_moderation_restrictions_user_community", "user_id", "community_id"),
        Index("ix_moderation_restrictions_report_id", "report_id"),
        Index("ix_moderation_restrictions_created_at", "created_at"),
    )


class DoctorVerificationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "doctor_verifications"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[VerificationStatus] = mapped_column(
        _verification_status_enum, nullable=False, default=VerificationStatus.PENDING
    )
    specialty: Mapped[str | None] = mapped_column(default=None)
    verifier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    verified_at: Mapped[datetime | None] = mapped_column(default=None)
    rejection_reason: Mapped[str | None] = mapped_column(default=None)
    revocation_reason: Mapped[str | None] = mapped_column(default=None)
    verification_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        UniqueConstraint("doctor_id", name="uq_doctor_verifications_doctor_id"),
        Index("ix_doctor_verifications_user_id", "user_id"),
        Index("ix_doctor_verifications_organization_id", "organization_id"),
        Index("ix_doctor_verifications_status", "status"),
    )
