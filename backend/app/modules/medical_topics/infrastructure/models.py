"""SQLAlchemy ORM models for the Medical Topics module.

Six tables: `medical_topics` (platform-wide, self-referencing `parent_id`
for hierarchy, many-to-one with `topic_specialties`), `topic_specialties`
(platform-wide vocabulary), `medical_topic_followers` (plain
`medical_topics` <-> `users` join), `medical_topic_aliases` (child of
`medical_topics`), `medical_topic_relations` (self-referencing
`medical_topics` <-> `medical_topics` join).

`medical_topic_followers`/`medical_topic_aliases`/`medical_topic_
relations` carry only `CreatedAtMixin` (`created_at`, no `updated_at`):
none of `MedicalTopicFollower`/`MedicalTopicAlias`/`MedicalTopicRelation`
has a single mutating method after `.create()` (a follow/alias/relation
is either present or absent, never itself edited) — the same shape
`app.modules.community.infrastructure.models.CommunityTagAssignmentModel`
already establishes for its own, identical join-row need; each mapper
synthesizes the domain aggregate's required `updated_at` field as equal
to `created_at` (see `infrastructure/mappers.py`'s own docstring).

`medical_topics`/`topic_specialties` carry no `AuditActorMixin` on the
latter — `TopicSpecialty`'s own domain model tracks no `created_by`/
`updated_by`, the same choice `CommunityCategoryModel` already makes for
itself.
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.medical_topics.domain.enums import TopicRelationType, TopicStatus, TopicVisibility

_topic_status_enum = pg_enum(TopicStatus, "topic_status_enum")
_topic_visibility_enum = pg_enum(TopicVisibility, "topic_visibility_enum")
_topic_relation_type_enum = pg_enum(TopicRelationType, "topic_relation_type_enum")


class MedicalTopicModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "medical_topics"

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    icon: Mapped[str | None] = mapped_column(Text, default=None)
    color: Mapped[str | None] = mapped_column(Text, default=None)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="SET NULL"), default=None
    )
    specialty_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topic_specialties.id", ondelete="SET NULL"), default=None
    )
    status: Mapped[TopicStatus] = mapped_column(
        _topic_status_enum, nullable=False, default=TopicStatus.DRAFT
    )
    visibility: Mapped[TopicVisibility] = mapped_column(
        _topic_visibility_enum, nullable=False, default=TopicVisibility.PUBLIC
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trending_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    popularity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index(
            "uq_medical_topics_slug",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_medical_topics_parent_id", "parent_id"),
        Index("ix_medical_topics_specialty_id", "specialty_id"),
        Index("ix_medical_topics_is_featured", "is_featured"),
        Index("ix_medical_topics_status", "status"),
        Index("ix_medical_topics_trending_score", "trending_score"),
        Index("ix_medical_topics_popularity_score", "popularity_score"),
    )


class TopicSpecialtyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "topic_specialties"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("name", name="uq_topic_specialties_name"),
        UniqueConstraint("slug", name="uq_topic_specialties_slug"),
    )


class MedicalTopicFollowerModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "medical_topic_followers"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("topic_id", "user_id", name="uq_medical_topic_followers_topic_id_user_id"),
        Index("ix_medical_topic_followers_topic_id", "topic_id"),
        Index("ix_medical_topic_followers_user_id", "user_id"),
    )


class MedicalTopicAliasModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "medical_topic_aliases"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("topic_id", "alias", name="uq_medical_topic_aliases_topic_id_alias"),
        Index("ix_medical_topic_aliases_topic_id", "topic_id"),
        Index("ix_medical_topic_aliases_alias", "alias"),
    )


class MedicalTopicRelationModel(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "medical_topic_relations"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )
    related_topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_topics.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[TopicRelationType] = mapped_column(
        _topic_relation_type_enum, nullable=False, default=TopicRelationType.RELATED
    )

    __table_args__ = (
        UniqueConstraint(
            "topic_id",
            "related_topic_id",
            name="uq_medical_topic_relations_topic_id_related_topic_id",
        ),
        Index("ix_medical_topic_relations_topic_id", "topic_id"),
        Index("ix_medical_topic_relations_related_topic_id", "related_topic_id"),
    )
