"""create family access grants table

Creates the Family / Caregiver Access foundation schema:
family_access_grants.

`organization_id` references `organizations.id`, `patient_id` references
`patients.id`, and `caregiver_user_id` references `users.id` (all
chained before this migration) — this is why this migration's
`down_revision` chains after the Documents migration, not a
modification to any prior module's tables. No column is added to, or
constraint changed on, `organizations`/`patients`/`users`/any other
prior table here.

`patient_id` uses `ON DELETE CASCADE`, matching every other per-patient
clinical table in this schema (`medical_documents`, `appointments`,
...). `caregiver_user_id` is a required, business-critical relationship
FK (not an optional audit-style attribution column) and uses
`ON DELETE RESTRICT`, matching `doctors.user_id`'s own required-reference
choice.

Two business rules are enforced as partial-unique indexes (defense in
depth, on top of the domain layer's own invariants, the same pattern
every prior module's own DB constraints already establish):
- "Invitation tokens must be unique" ->
  `uq_family_access_grants_invitation_token`, scoped `WHERE deleted_at
  IS NULL` like every other soft-delete-aware uniqueness constraint in
  this schema.
- "One caregiver cannot have duplicate active access to the same
  patient" -> `uq_family_access_grants_active_patient_caregiver`, a
  partial unique index on `(patient_id, caregiver_user_id)` scoped
  `WHERE status IN ('pending', 'accepted') AND deleted_at IS NULL`.

Revision ID: c3f8a1d9e6b2
Revises: b7e3a9f2c6d4
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3f8a1d9e6b2"
down_revision: str | None = "b7e3a9f2c6d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TIMESTAMPTZ = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def _audit_columns() -> list[sa.Column]:
    """The five standard columns every table in this schema carries, minus
    `id` (added separately since its type/default is identical everywhere
    but declared first). See `docs/database/00_overview.md`.
    """
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
    relationship_enum = postgresql.ENUM(
        "parent",
        "child",
        "spouse",
        "sibling",
        "guardian",
        "caregiver",
        "relative",
        "friend",
        "other",
        name="family_access_relationship_enum",
        create_type=False,
    )
    relationship_enum.create(op.get_bind(), checkfirst=True)

    access_level_enum = postgresql.ENUM(
        "read_only",
        "limited_medical",
        "full_medical",
        name="family_access_level_enum",
        create_type=False,
    )
    access_level_enum.create(op.get_bind(), checkfirst=True)

    status_enum = postgresql.ENUM(
        "pending",
        "accepted",
        "rejected",
        "revoked",
        "expired",
        name="family_access_status_enum",
        create_type=False,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "family_access_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("caregiver_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship", relationship_enum, nullable=False),
        sa.Column("access_level", access_level_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("invitation_token", sa.Text(), nullable=False),
        sa.Column("invitation_expires_at", _TIMESTAMPTZ, nullable=False),
        sa.Column("accepted_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("revoked_at", _TIMESTAMPTZ, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_family_access_grants"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_family_access_grants_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_family_access_grants_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["caregiver_user_id"],
            ["users.id"],
            name="fk_family_access_grants_caregiver_user_id_users",
            ondelete="RESTRICT",
        ),
        *_audit_fks("family_access_grants"),
    )
    op.create_index(
        "uq_family_access_grants_invitation_token",
        "family_access_grants",
        ["invitation_token"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_family_access_grants_active_patient_caregiver",
        "family_access_grants",
        ["patient_id", "caregiver_user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'accepted') AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_family_access_grants_organization_id", "family_access_grants", ["organization_id"]
    )
    op.create_index("ix_family_access_grants_patient_id", "family_access_grants", ["patient_id"])
    op.create_index(
        "ix_family_access_grants_caregiver_user_id", "family_access_grants", ["caregiver_user_id"]
    )


def downgrade() -> None:
    op.drop_table("family_access_grants")

    postgresql.ENUM(name="family_access_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="family_access_level_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="family_access_relationship_enum").drop(op.get_bind(), checkfirst=True)
