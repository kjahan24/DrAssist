"""SQLAlchemy ORM models for the Community module.

Two tables: `communities` (many-to-one with `organizations`),
`community_members` (many-to-one with both `communities` and `users`).

`created_by`/`updated_by` on `communities` (via `AuditActorMixin`)
reference `users.id` — the Authentication module's table — the same way
every table in this schema does. `community_members` carries no
`AuditActorMixin`/`SoftDeleteMixin`: a membership row's own `user_id`
already identifies who it belongs to, and `status` (cycling between
`ACTIVE`/`LEFT`) already *is* this table's soft-delete — see
`app.modules.community.domain.repositories.CommunityMemberRepository`'s
own docstring.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, func, text
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

    __table_args__ = (
        Index(
            "uq_communities_organization_id_slug",
            "organization_id",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_communities_organization_id", "organization_id"),
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
