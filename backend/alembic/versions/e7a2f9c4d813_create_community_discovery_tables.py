"""create community discovery tables

Phase 5.2 — Communities module: adds `community_categories` (a
platform-wide, admin-extensible vocabulary — seeded here with ten
starter categories per this task's own CATEGORIES section, but not
closed: `CreateCommunityCategoryService` can add more without a further
migration), `community_tags` (reusable, searchable medical tags),
`community_tag_assignments` (the `communities` <-> `community_tags`
join), and `community_rules` (per-community, ordered, enable/disable-
able). Also extends `communities` with `category_id` (nullable FK),
`avatar_storage_path`/`banner_storage_path` (nullable, storage keys —
see `UpdateCommunityAppearanceService`'s own docstring), and
`is_verified`/`is_featured` (both default `false`).

No column is added to, or constraint changed on, any table this
migration doesn't itself create — `communities`' own five new columns
are the only alteration to a Phase 5.1 table, and all five are nullable/
defaulted, so every existing row remains valid without a backfill.

Revision ID: e7a2f9c4d813
Revises: d8f3c6a1b425
Create Date: 2026-08-05

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7a2f9c4d813"
down_revision: str | None = "d8f3c6a1b425"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")

_STARTER_CATEGORIES = [
    ("Cardiology", "cardiology"),
    ("Dermatology", "dermatology"),
    ("Neurology", "neurology"),
    ("Pediatrics", "pediatrics"),
    ("Oncology", "oncology"),
    ("Gynecology", "gynecology"),
    ("Mental Health", "mental-health"),
    ("Diabetes", "diabetes"),
    ("Nutrition", "nutrition"),
    ("General Medicine", "general-medicine"),
]


def upgrade() -> None:
    # --- community_categories ------------------------------------------------
    op.create_table(
        "community_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_community_categories"),
        sa.UniqueConstraint("name", name="uq_community_categories_name"),
        sa.UniqueConstraint("slug", name="uq_community_categories_slug"),
    )

    categories_table = sa.table(
        "community_categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.Text()),
        sa.column("slug", sa.Text()),
    )
    op.bulk_insert(
        categories_table,
        [{"id": uuid.uuid4(), "name": name, "slug": slug} for name, slug in _STARTER_CATEGORIES],
    )

    # --- community_tags -----------------------------------------------------
    op.create_table(
        "community_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_community_tags"),
        sa.UniqueConstraint("name", name="uq_community_tags_name"),
    )

    # --- community_tag_assignments -------------------------------------------
    op.create_table(
        "community_tag_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_community_tag_assignments"),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_tag_assignments_community_id_communities",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["community_tags.id"],
            name="fk_community_tag_assignments_tag_id_community_tags",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "community_id",
            "tag_id",
            name="uq_community_tag_assignments_community_id_tag_id",
        ),
    )
    op.create_index(
        "ix_community_tag_assignments_community_id",
        "community_tag_assignments",
        ["community_id"],
    )
    op.create_index("ix_community_tag_assignments_tag_id", "community_tag_assignments", ["tag_id"])

    # --- community_rules -------------------------------------------------------
    op.create_table(
        "community_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_community_rules"),
        sa.ForeignKeyConstraint(
            ["community_id"],
            ["communities.id"],
            name="fk_community_rules_community_id_communities",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_community_rules_community_id", "community_rules", ["community_id"])

    # --- communities: new columns ---------------------------------------------
    op.add_column(
        "communities", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column("communities", sa.Column("avatar_storage_path", sa.Text(), nullable=True))
    op.add_column("communities", sa.Column("banner_storage_path", sa.Text(), nullable=True))
    op.add_column(
        "communities",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "communities",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_foreign_key(
        "fk_communities_category_id_community_categories",
        "communities",
        "community_categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_communities_category_id", "communities", ["category_id"])
    op.create_index("ix_communities_is_featured", "communities", ["is_featured"])


def downgrade() -> None:
    op.drop_index("ix_communities_is_featured", table_name="communities")
    op.drop_index("ix_communities_category_id", table_name="communities")
    op.drop_constraint(
        "fk_communities_category_id_community_categories", "communities", type_="foreignkey"
    )
    op.drop_column("communities", "is_featured")
    op.drop_column("communities", "is_verified")
    op.drop_column("communities", "banner_storage_path")
    op.drop_column("communities", "avatar_storage_path")
    op.drop_column("communities", "category_id")

    op.drop_table("community_rules")
    op.drop_table("community_tag_assignments")
    op.drop_table("community_tags")
    op.drop_table("community_categories")
