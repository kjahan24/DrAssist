"""create community tables

Creates the Community module's foundation schema: communities
(many-to-one with organizations), community_members (many-to-one with
both communities and users).

`created_by`/`updated_by` on `communities` reference `users.id` (the
Authentication module's table), via the same shared `AuditActorMixin`
every table in this schema uses. No column is added to, or constraint
changed on, any existing table — this migration only adds two new ones.

Revision ID: d8f3c6a1b425
Revises: c3f8a1d9e6b2
Create Date: 2026-08-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8f3c6a1b425"
down_revision: str | None = "c3f8a1d9e6b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def _audit_columns() -> list[sa.Column]:
    """The five standard columns every soft-deletable table in this schema
    carries, minus `id` (added separately since its type/default is
    identical everywhere but declared first). See
    `docs/database/00_overview.md`."""
    return [
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("deleted_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def _audit_fks(table: str) -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=f"fk_{table}_created_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=f"fk_{table}_updated_by_users", ondelete="SET NULL"
        ),
    ]


def upgrade() -> None:
    community_visibility_enum = postgresql.ENUM(
        "public", "verified_only", "private",
        name="community_visibility_enum",
        create_type=False,
    )
    community_visibility_enum.create(op.get_bind(), checkfirst=True)

    community_role_enum = postgresql.ENUM(
        "member", "moderator", "admin", "owner",
        name="community_role_enum",
        create_type=False,
    )
    community_role_enum.create(op.get_bind(), checkfirst=True)

    community_member_status_enum = postgresql.ENUM(
        "active", "invited", "blocked", "left",
        name="community_member_status_enum",
        create_type=False,
    )
    community_member_status_enum.create(op.get_bind(), checkfirst=True)

    # --- communities -------------------------------------------------------
    op.create_table(
        "communities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "visibility", community_visibility_enum, nullable=False, server_default="public"
        ),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_communities"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_communities_organization_id_organizations",
            ondelete="CASCADE",
        ),
        *_audit_fks("communities"),
    )
    op.create_index(
        "uq_communities_organization_id_slug",
        "communities",
        ["organization_id", "slug"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_communities_organization_id", "communities", ["organization_id"])

    # --- community_members ---------------------------------------------------
    op.create_table(
        "community_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", community_role_enum, nullable=False, server_default="member"),
        sa.Column(
            "status", community_member_status_enum, nullable=False, server_default="active"
        ),
        sa.Column("joined_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_community_members"),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_members_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_community_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "community_id", "user_id", name="uq_community_members_community_id_user_id"
        ),
    )
    op.create_index(
        "ix_community_members_community_id", "community_members", ["community_id"]
    )
    op.create_index("ix_community_members_user_id", "community_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("community_members")
    op.drop_table("communities")

    postgresql.ENUM(name="community_member_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="community_role_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="community_visibility_enum").drop(op.get_bind(), checkfirst=True)
