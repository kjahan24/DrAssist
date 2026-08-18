"""create community engagement tables

Phase 5.8 — Community Voting & Engagement module: creates five tables —
`votes`, `saved_content`, `topic_followers`, `community_followers`,
`doctor_followers` — this task's own DATABASE section names all five as
distinct tables (not one generic polymorphic engagement table).

`votes.target_id`/`saved_content.target_id` have deliberately no foreign
key — a single column cannot reference `community_posts`/
`community_questions`/`community_answers`/`community_comments`
conditionally at the schema level, the same "polymorphic reference,
validated at write time through each peer module's own public query
port instead" pattern `community_comments.target_id` already establishes
for itself (Phase 5.7).

Critical uniqueness constraints (this task's own literal DATABASE
requirement): `(user_id, target_type, target_id)` on both `votes` and
`saved_content`; the analogous one-row-per-relationship constraint on
each follower table (`(user_id, topic_id)`/`(user_id, community_id)`/
`(follower_user_id, followed_user_id)`). `doctor_followers` additionally
carries a `CHECK` constraint (`follower_user_id != followed_user_id`)
enforcing "Users cannot follow themselves" at the database level, as a
concurrency safety net under `FollowDoctorService`'s own application-
level check.

None of these five tables has a `deleted_at`/soft-delete column, nor a
`status` enum — see `app.modules.community_engagement.domain.entities`'s
own module docstring: a vote/save/follow either currently exists or it
is a genuine, hard-deleted row; there is no lifecycle worth preserving.
`votes` is the only one of the five with an `updated_at` column, since
`Vote.switch()` (vote switching, upvote <-> downvote) is the one real
in-place mutation across all five aggregates.

No existing table (from any prior phase) is altered by this migration —
five wholly new tables only.

Revision ID: 2be7bd77eb69
Revises: d2627788d3c5
Create Date: 2026-08-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2be7bd77eb69"
down_revision: str | None = "d2627788d3c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    engagement_target_type_enum = postgresql.ENUM(
        "post",
        "question",
        "answer",
        "comment",
        name="engagement_target_type_enum",
        create_type=False,
    )
    engagement_target_type_enum.create(op.get_bind(), checkfirst=True)

    vote_type_enum = postgresql.ENUM("upvote", "downvote", name="vote_type_enum", create_type=False)
    vote_type_enum.create(op.get_bind(), checkfirst=True)

    # --- votes -----------------------------------------------------------------
    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", engagement_target_type_enum, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vote_type", vote_type_enum, nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_votes"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_votes_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_votes_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "target_type", "target_id", name="uq_votes_user_id_target_type_target_id"
        ),
    )
    op.create_index("ix_votes_target_type_target_id", "votes", ["target_type", "target_id"])
    op.create_index("ix_votes_user_id", "votes", ["user_id"])
    op.create_index("ix_votes_organization_id", "votes", ["organization_id"])
    op.create_index("ix_votes_vote_type", "votes", ["vote_type"])
    op.create_index("ix_votes_created_at", "votes", ["created_at"])

    # --- saved_content -----------------------------------------------------------
    op.create_table(
        "saved_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", engagement_target_type_enum, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_saved_content"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_saved_content_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_saved_content_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "target_type",
            "target_id",
            name="uq_saved_content_user_id_target_type_target_id",
        ),
    )
    op.create_index(
        "ix_saved_content_target_type_target_id", "saved_content", ["target_type", "target_id"]
    )
    op.create_index("ix_saved_content_user_id", "saved_content", ["user_id"])
    op.create_index("ix_saved_content_organization_id", "saved_content", ["organization_id"])
    op.create_index("ix_saved_content_created_at", "saved_content", ["created_at"])

    # --- topic_followers -----------------------------------------------------------
    op.create_table(
        "topic_followers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_topic_followers"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_topic_followers_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_topic_followers_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_topic_followers_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_topic_followers_user_id_topic_id"),
    )
    op.create_index("ix_topic_followers_topic_id", "topic_followers", ["topic_id"])
    op.create_index("ix_topic_followers_user_id", "topic_followers", ["user_id"])
    op.create_index("ix_topic_followers_organization_id", "topic_followers", ["organization_id"])
    op.create_index("ix_topic_followers_created_at", "topic_followers", ["created_at"])

    # --- community_followers -----------------------------------------------------
    op.create_table(
        "community_followers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_followers"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_community_followers_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_community_followers_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_followers_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "community_id", name="uq_community_followers_user_id_community_id"
        ),
    )
    op.create_index("ix_community_followers_community_id", "community_followers", ["community_id"])
    op.create_index("ix_community_followers_user_id", "community_followers", ["user_id"])
    op.create_index(
        "ix_community_followers_organization_id", "community_followers", ["organization_id"]
    )
    op.create_index("ix_community_followers_created_at", "community_followers", ["created_at"])

    # --- doctor_followers -----------------------------------------------------------
    op.create_table(
        "doctor_followers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("follower_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("followed_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_followers"),
        sa.ForeignKeyConstraint(
            ["follower_user_id"],
            ["users.id"],
            name="fk_doctor_followers_follower_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_doctor_followers_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["followed_user_id"],
            ["users.id"],
            name="fk_doctor_followers_followed_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "follower_user_id",
            "followed_user_id",
            name="uq_doctor_followers_follower_user_id_followed_user_id",
        ),
        sa.CheckConstraint(
            "follower_user_id != followed_user_id", name="ck_doctor_followers_no_self_follow"
        ),
    )
    op.create_index(
        "ix_doctor_followers_followed_user_id", "doctor_followers", ["followed_user_id"]
    )
    op.create_index(
        "ix_doctor_followers_follower_user_id", "doctor_followers", ["follower_user_id"]
    )
    op.create_index("ix_doctor_followers_organization_id", "doctor_followers", ["organization_id"])
    op.create_index("ix_doctor_followers_created_at", "doctor_followers", ["created_at"])


def downgrade() -> None:
    op.drop_table("doctor_followers")
    op.drop_table("community_followers")
    op.drop_table("topic_followers")
    op.drop_table("saved_content")
    op.drop_table("votes")

    postgresql.ENUM(name="vote_type_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="engagement_target_type_enum").drop(op.get_bind(), checkfirst=True)
