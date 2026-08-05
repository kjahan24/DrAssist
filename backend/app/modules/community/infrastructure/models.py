"""SQLAlchemy ORM models for the Community module.

Six tables: `communities` (many-to-one with `organizations`),
`community_members` (many-to-one with both `communities` and `users`),
`community_categories` (platform-wide vocabulary, Phase 5.2),
`community_tags` (platform-wide, reusable, Phase 5.2), `community_tags_
assignments` (plain `communities` <-> `community_tags` join, Phase 5.2),
`community_rules` (many-to-one with `communities`, Phase 5.2).

`created_by`/`updated_by` on `communities` (via `AuditActorMixin`)
reference `users.id` — the Authentication module's table — the same way
every table in this schema does. `community_members` carries no
`AuditActorMixin`/`SoftDeleteMixin`: a membership row's own `user_id`
already identifies who it belongs to, and `status` (cycling between
`ACTIVE`/`LEFT`) already *is* this table's soft-delete — see
`app.modules.community.domain.repositories.CommunityMemberRepository`'s
own docstring. `community_categories`/`community_tags`/`community_rules`
carry no `AuditActorMixin` either — none of these three entities' own
domain models track `created_by`/`updated_by` (see each one's own
docstring in `domain/entities.py`).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)

_community_visibility_enum = pg_enum(CommunityVisibility, "community_visibility_enum")
_community_role_enum = pg_enum(CommunityRole, "community_role_enum")
_community_member_status_enum = pg_enum(CommunityMemberStatus, "community_member_status_enum")


class CommunityModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "communities"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    visibility: Mapped[CommunityVisibility] = mapped_column(
        _community_visibility_enum, nullable=False, default=CommunityVisibility.PUBLIC
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("community_categories.id", ondelete="SET NULL"), default=None
    )
    avatar_storage_path: Mapped[str | None] = mapped_column(Text, default=None)
    banner_storage_path: Mapped[str | None] = mapped_column(Text, default=None)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index(
            "uq_communities_organization_id_slug",
            "organization_id",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_communities_organization_id", "organization_id"),
        Index("ix_communities_category_id", "category_id"),
        Index("ix_communities_is_featured", "is_featured"),
    )


class CommunityMemberModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_members"

    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[CommunityRole] = mapped_column(
        _community_role_enum, nullable=False, default=CommunityRole.MEMBER
    )
    status: Mapped[CommunityMemberStatus] = mapped_column(
        _community_member_status_enum, nullable=False, default=CommunityMemberStatus.ACTIVE
    )
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "community_id", "user_id", name="uq_community_members_community_id_user_id"
        ),
        Index("ix_community_members_community_id", "community_id"),
        Index("ix_community_members_user_id", "user_id"),
    )


class CommunityCategoryModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_categories"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("name", name="uq_community_categories_name"),
        UniqueConstraint("slug", name="uq_community_categories_slug"),
    )


class CommunityTagModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_tags"

    name: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("name", name="uq_community_tags_name"),)


class CommunityTagAssignmentModel(Base, UUIDPrimaryKeyMixin):
    """Plain `communities` <-> `community_tags` join row — no
    `TimestampMixin`/`updated_at` (an assignment is either present or
    absent, never itself edited), matching the shape `AuditActorMixin`-
    free join tables elsewhere in this schema already use for
    themselves; `created_at` alone still records *when* it was
    assigned."""

    __tablename__ = "community_tag_assignments"

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("community_tags.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "community_id", "tag_id", name="uq_community_tag_assignments_community_id_tag_id"
        ),
        Index("ix_community_tag_assignments_community_id", "community_id"),
        Index("ix_community_tag_assignments_tag_id", "tag_id"),
    )


class CommunityRuleModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_rules"

    community_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (Index("ix_community_rules_community_id", "community_id"),)
