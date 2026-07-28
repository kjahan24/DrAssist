"""create patient contacts tables

Creates the Patient Contacts foundation schema: patient_contacts,
emergency_contacts, insurances — all three many-to-one with `patients`
(the Patient module's own table).

`organization_id` on all three tables references `organizations.id` and
`patient_id` references `patients.id` — this is why this migration's
`down_revision` chains after the Patient migration, not a modification to
any prior module's tables. No column is added to, or constraint changed
on, `organizations`/`patients`/`doctors`/`users`/any other prior table
here.

Revision ID: d4b5f3913c60
Revises: 9aac8d22f92d
Create Date: 2026-07-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4b5f3913c60"
down_revision: str | None = "9aac8d22f92d"
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
    contact_type_enum = postgresql.ENUM(
        "mobile",
        "home",
        "office",
        "other",
        name="contact_type_enum",
        create_type=False,
    )
    contact_type_enum.create(op.get_bind(), checkfirst=True)

    insurance_status_enum = postgresql.ENUM(
        "active",
        "inactive",
        "cancelled",
        name="insurance_status_enum",
        create_type=False,
    )
    insurance_status_enum.create(op.get_bind(), checkfirst=True)

    # --- patient_contacts ------------------------------------------------
    op.create_table(
        "patient_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_type", contact_type_enum, nullable=False),
        sa.Column("phone_number", sa.Text(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_patient_contacts"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_patient_contacts_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_patient_contacts_patient_id_patients",
            ondelete="CASCADE",
        ),
        *_audit_fks("patient_contacts"),
    )
    op.create_index(
        "uq_patient_contacts_primary_per_type",
        "patient_contacts",
        ["patient_id", "contact_type"],
        unique=True,
        postgresql_where=sa.text("is_primary AND deleted_at IS NULL"),
    )
    op.create_index("ix_patient_contacts_patient_id", "patient_contacts", ["patient_id"])

    # --- emergency_contacts -------------------------------------------------
    op.create_table(
        "emergency_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("relationship", sa.Text(), nullable=False),
        sa.Column("phone_number", sa.Text(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_emergency_contacts"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_emergency_contacts_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_emergency_contacts_patient_id_patients",
            ondelete="CASCADE",
        ),
        *_audit_fks("emergency_contacts"),
    )
    op.create_index(
        "uq_emergency_contacts_primary_per_patient",
        "emergency_contacts",
        ["patient_id"],
        unique=True,
        postgresql_where=sa.text("is_primary AND deleted_at IS NULL"),
    )
    op.create_index("ix_emergency_contacts_patient_id", "emergency_contacts", ["patient_id"])

    # --- insurances -----------------------------------------------------------
    op.create_table(
        "insurances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("policy_number", sa.Text(), nullable=False),
        sa.Column("member_id", sa.Text(), nullable=True),
        sa.Column("group_number", sa.Text(), nullable=True),
        sa.Column("coverage_type", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("status", insurance_status_enum, nullable=False, server_default="active"),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_insurances"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_insurances_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_insurances_patient_id_patients",
            ondelete="CASCADE",
        ),
        *_audit_fks("insurances"),
        sa.CheckConstraint("expiry_date > effective_date", name="expiry_after_effective"),
    )
    op.create_index("ix_insurances_patient_id", "insurances", ["patient_id"])


def downgrade() -> None:
    op.drop_table("insurances")
    op.drop_table("emergency_contacts")
    op.drop_table("patient_contacts")

    postgresql.ENUM(name="insurance_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="contact_type_enum").drop(op.get_bind(), checkfirst=True)
