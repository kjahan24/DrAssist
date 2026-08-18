"""SQLAlchemy ORM models for the Community Engagement module.

Five tables: `votes`, `saved_content`, `topic_followers`,
`community_followers`, `doctor_followers` — this task's own DATABASE
section names all five as distinct tables (not one generic polymorphic
"engagement" table), so that is exactly what is modeled here.

`votes.target_id`/`saved_content.target_id` have deliberately no foreign
key — a single column cannot reference `community_posts`/
`community_questions`/`community_answers`/`community_comments`
conditionally at the schema level. Existence, tenant ownership, and
"open to engagement" (`PUBLISHED`) validation happens once, at write
time, through each peer module's own public query port instead — see
`_target_resolution.py`'s own docstring.

`VoteModel` is the only one of the five with `TimestampMixin` (both
`created_at` and `updated_at`) — `Vote.switch()` is the one real mutation
across all five aggregates (see `entities.py`'s own module docstring);
`SavedContentModel`/`TopicFollowerModel`/`CommunityFollowerModel`/
`DoctorFollowerModel` all use `CreatedAtMixin` only, since none of them
is ever mutated in place — a save/follow either exists or is removed
(hard-deleted), never edited.

The unique constraints below are this task's own literal "Critical
uniqueness constraints: `(user_id, target_type, target_id)` for votes
and saves as appropriate" DATABASE requirement, plus the analogous
one-row-per-relationship constraint for each of the three follower
tables (`(user_id, topic_id)`/`(user_id, community_id)`/
`(follower_user_id, followed_user_id)`) — each doubles as the concurrency
safety net backing "Prevent duplicate votes"/"duplicate follows/saves"
underneath the application layer's own idempotency checks, the same
"DB constraint as a safety net under the application-level coordination"
pattern `app.modules.community_answers.infrastructure.models
.CommunityAnswerModel`'s own `uq_community_answers_question_id_best`
partial index already establishes.

`DoctorFollowerModel` additionally carries a `CHECK` constraint
preventing `follower_user_id == followed_user_id` at the database level
— "Users cannot follow themselves," enforced twice: once by
`FollowDoctorService` itself, and again here as a safety net.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.community_engagement.domain.enums import EngagementTargetType, VoteType

_engagement_target_type_enum = pg_enum(EngagementTargetType, "engagement_target_type_enum")
_vote_type_enum = pg_enum(VoteType, "vote_type_enum")


class VoteModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "votes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[EngagementTargetType] = mapped_column(
        _engagement_target_type_enum, nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    vote_type: Mapped[VoteType] = mapped_column(_vote_type_enum, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "target_type", "target_id", name="uq_votes_user_id_target_type_target_id"
        ),
        Index("ix_votes_target_type_target_id", "target_type", "target_id"),
        Index("ix_votes_user_id", "user_id"),
        Index("ix_votes_organization_id", "organization_id"),
        Index("ix_votes_vote_type", "vote_type"),
        Index("ix_votes_created_at", "created_at"),
    )


class SavedContentModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "saved_content"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[EngagementTargetType] = mapped_column(
        _engagement_target_type_enum, nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "target_type",
            "target_id",
            name="uq_saved_content_user_id_target_type_target_id",
        ),
        Index("ix_saved_content_target_type_target_id", "target_type", "target_id"),
        Index("ix_saved_content_user_id", "user_id"),
        Index("ix_saved_content_organization_id", "organization_id"),
        Index("ix_saved_content_created_at", "created_at"),
    )


class TopicFollowerModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "topic_followers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_topic_followers_user_id_topic_id"),
        Index("ix_topic_followers_topic_id", "topic_id"),
        Index("ix_topic_followers_user_id", "user_id"),
        Index("ix_topic_followers_organization_id", "organization_id"),
        Index("ix_topic_followers_created_at", "created_at"),
    )


class CommunityFollowerModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "community_followers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "community_id", name="uq_community_followers_user_id_community_id"
        ),
        Index("ix_community_followers_community_id", "community_id"),
        Index("ix_community_followers_user_id", "user_id"),
        Index("ix_community_followers_organization_id", "organization_id"),
        Index("ix_community_followers_created_at", "created_at"),
    )


class DoctorFollowerModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "doctor_followers"

    follower_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    followed_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "follower_user_id",
            "followed_user_id",
            name="uq_doctor_followers_follower_user_id_followed_user_id",
        ),
        CheckConstraint(
            "follower_user_id != followed_user_id", name="ck_doctor_followers_no_self_follow"
        ),
        Index("ix_doctor_followers_followed_user_id", "followed_user_id"),
        Index("ix_doctor_followers_follower_user_id", "follower_user_id"),
        Index("ix_doctor_followers_organization_id", "organization_id"),
        Index("ix_doctor_followers_created_at", "created_at"),
    )
