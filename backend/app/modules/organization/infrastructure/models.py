"""SQLAlchemy ORM models for the Organization module.

Three tables: `organizations`, `organization_settings` (one-to-one with
`organizations`, enforced via a partial unique index on `organization_id`),
`departments` (many-to-one with `organizations`). See
`app.modules.organization.container` for the module's scope note.

`created_by`/`updated_by` (via `AuditActorMixin`) reference `users.id` —
the Authentication module's table — the same way every table in this
schema does; this is *using* the shared mixin already established in
`app/infrastructure/database/base.py`, not a modification to the
Authentication module itself.
"""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SAEnum

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.modules.organization.domain.enums import DepartmentStatus, OrganizationType

_organization_type_enum = SAEnum(
    OrganizationType,
    name="organization_type_enum",
    create_type=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

_department_status_enum = SAEnum(
    DepartmentStatus,
    name="department_status_enum",
    create_type=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class OrganizationModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "organizations"

    organization_code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(Text, default=None)
    type: Mapped[OrganizationType] = mapped_column(_organization_type_enum, nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT, default=None)
    phone: Mapped[str | None] = mapped_column(Text, default=None)
    website: Mapped[str | None] = mapped_column(Text, default=None)
    logo_url: Mapped[str | None] = mapped_column(Text, default=None)
    tax_number: Mapped[str | None] = mapped_column(Text, default=None)
    registration_number: Mapped[str | None] = mapped_column(Text, default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    city: Mapped[str | None] = mapped_column(Text, default=None)
    state: Mapped[str | None] = mapped_column(Text, default=None)
    country: Mapped[str | None] = mapped_column(Text, default=None)
    postal_code: Mapped[str | None] = mapped_column(Text, default=None)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    language: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index(
            "uq_organizations_organization_code",
            "organization_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_organizations_is_active", "is_active"),
    )


class OrganizationSettingsModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "organization_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    working_hours: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    appointment_duration_minutes: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=30
    )
    default_timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    default_language: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    default_currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    feature_flags: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ai_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notification_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        Index(
            "uq_organization_settings_organization_id",
            "organization_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class DepartmentModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "departments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[DepartmentStatus] = mapped_column(
        _department_status_enum, nullable=False, default=DepartmentStatus.ACTIVE
    )

    __table_args__ = (Index("ix_departments_organization_id", "organization_id"),)
