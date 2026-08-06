"""create medical topics tables

Phase 5.3 — Medical Topics module: creates `topic_specialties` (a
platform-wide, admin-extensible vocabulary — seeded here with ten
starter specialties per this task's own SPECIALTIES section, but not
closed: `CreateTopicSpecialtyService` can add more without a further
migration, the same "seed, don't close" shape
`e7a2f9c4d813_create_community_discovery_tables`'s own
`community_categories` already establishes), `medical_topics` (self-
referencing `parent_id` for the Parent/Child hierarchy, `specialty_id`
FK), `medical_topic_followers` (the `medical_topics` <-> `users` join,
"Follow Topic"/"Topic followers"), `medical_topic_aliases` (child of
`medical_topics`, "Topic aliases"/"Topic synonyms"), and
`medical_topic_relations` (self-referencing `medical_topics` <->
`medical_topics` join, "Related Topics").

This module is deliberately platform-wide, not organization-scoped — see
`app.modules.medical_topics.domain.repositories.MedicalTopicRepository`'s
own docstring — so no table here carries an `organization_id` column.

No existing table (from any prior phase) is altered by this migration —
five wholly new tables only.

Revision ID: bef8b3fd9a86
Revises: e7a2f9c4d813
Create Date: 2026-08-06

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "bef8b3fd9a86"
down_revision: str | None = "e7a2f9c4d813"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")

_STARTER_SPECIALTIES = [
    ("Cardiology", "cardiology"),
    ("Dermatology", "dermatology"),
    ("Neurology", "neurology"),
    ("Oncology", "oncology"),
    ("Pediatrics", "pediatrics"),
    ("Psychiatry", "psychiatry"),
    ("Gynecology", "gynecology"),
    ("Endocrinology", "endocrinology"),
    ("Orthopedics", "orthopedics"),
    ("General Medicine", "general-medicine"),
]


def upgrade() -> None:
    topic_status_enum = postgresql.ENUM(
        "draft", "published", "archived", name="topic_status_enum", create_type=False
    )
    topic_status_enum.create(op.get_bind(), checkfirst=True)

    topic_visibility_enum = postgresql.ENUM(
        "public", "unlisted", "private", name="topic_visibility_enum", create_type=False
    )
    topic_visibility_enum.create(op.get_bind(), checkfirst=True)

    topic_relation_type_enum = postgresql.ENUM(
        "related", "see_also", name="topic_relation_type_enum", create_type=False
    )
    topic_relation_type_enum.create(op.get_bind(), checkfirst=True)

    # --- topic_specialties -----------------------------------------------------
    op.create_table(
        "topic_specialties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.PrimaryKeyConstraint("id", name="pk_topic_specialties"),
        sa.UniqueConstraint("name", name="uq_topic_specialties_name"),
        sa.UniqueConstraint("slug", name="uq_topic_specialties_slug"),
    )

    specialties_table = sa.table(
        "topic_specialties",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.Text()),
        sa.column("slug", sa.Text()),
    )
    op.bulk_insert(
        specialties_table,
        [{"id": uuid.uuid4(), "name": name, "slug": slug} for name, slug in _STARTER_SPECIALTIES],
    )

    # --- medical_topics ----------------------------------------------------------
    op.create_table(
        "medical_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("specialty_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", topic_status_enum, nullable=False, server_default="draft"),
        sa.Column("visibility", topic_visibility_enum, nullable=False, server_default="public"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trending_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("popularity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("deleted_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_medical_topics"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["medical_topics.id"],
            name="fk_medical_topics_parent_id_medical_topics",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["specialty_id"],
            ["topic_specialties.id"],
            name="fk_medical_topics_specialty_id_topic_specialties",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_medical_topics_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_medical_topics_updated_by_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "uq_medical_topics_slug",
        "medical_topics",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_medical_topics_parent_id", "medical_topics", ["parent_id"])
    op.create_index("ix_medical_topics_specialty_id", "medical_topics", ["specialty_id"])
    op.create_index("ix_medical_topics_is_featured", "medical_topics", ["is_featured"])
    op.create_index("ix_medical_topics_status", "medical_topics", ["status"])
    op.create_index("ix_medical_topics_trending_score", "medical_topics", ["trending_score"])
    op.create_index("ix_medical_topics_popularity_score", "medical_topics", ["popularity_score"])

    # --- medical_topic_followers ---------------------------------------------------
    op.create_table(
        "medical_topic_followers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_medical_topic_followers"),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_medical_topic_followers_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_medical_topic_followers_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "topic_id", "user_id", name="uq_medical_topic_followers_topic_id_user_id"
        ),
    )
    op.create_index("ix_medical_topic_followers_topic_id", "medical_topic_followers", ["topic_id"])
    op.create_index("ix_medical_topic_followers_user_id", "medical_topic_followers", ["user_id"])

    # --- medical_topic_aliases -----------------------------------------------------
    op.create_table(
        "medical_topic_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_medical_topic_aliases"),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_medical_topic_aliases_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("topic_id", "alias", name="uq_medical_topic_aliases_topic_id_alias"),
    )
    op.create_index("ix_medical_topic_aliases_topic_id", "medical_topic_aliases", ["topic_id"])
    op.create_index("ix_medical_topic_aliases_alias", "medical_topic_aliases", ["alias"])

    # --- medical_topic_relations -----------------------------------------------------
    op.create_table(
        "medical_topic_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", _TIMESTAMPTZ, nullable=False, server_default=_NOW),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "relation_type", topic_relation_type_enum, nullable=False, server_default="related"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_medical_topic_relations"),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["medical_topics.id"],
            name="fk_medical_topic_relations_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_topic_id"],
            ["medical_topics.id"],
            name="fk_medical_topic_relations_related_topic_id_medical_topics",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "topic_id",
            "related_topic_id",
            name="uq_medical_topic_relations_topic_id_related_topic_id",
        ),
    )
    op.create_index("ix_medical_topic_relations_topic_id", "medical_topic_relations", ["topic_id"])
    op.create_index(
        "ix_medical_topic_relations_related_topic_id",
        "medical_topic_relations",
        ["related_topic_id"],
    )


def downgrade() -> None:
    op.drop_table("medical_topic_relations")
    op.drop_table("medical_topic_aliases")
    op.drop_table("medical_topic_followers")
    op.drop_table("medical_topics")
    op.drop_table("topic_specialties")

    postgresql.ENUM(name="topic_relation_type_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="topic_visibility_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="topic_status_enum").drop(op.get_bind(), checkfirst=True)
