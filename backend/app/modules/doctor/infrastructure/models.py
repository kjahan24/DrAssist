"""SQLAlchemy ORM models for the Doctor module.

Five tables: `doctors`, `doctor_profiles` (one-to-one with `doctors`),
`doctor_licenses`, `doctor_specializations`, `doctor_schedules`
(many-to-one with `doctors`). See `app.modules.doctor.container` for the
module's scope note.

`doctors.organization_id` and `doctor_specializations.organization_id`
carry real foreign keys to `organizations.id`, and `doctors.user_id` a
real foreign key to `users.id` — unlike the Authentication module's
`organization_id` columns (deferred because the Organization module did
not exist yet when those were written), these are brand-new columns on
brand-new tables, so there is no backward-compatibility reason to defer
them. Neither `organizations` nor `users` is modified by this migration.
"""

import uuid
from datetime import date, time
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SAEnum

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.modules.doctor.domain.enums import (
    DayOfWeek,
    DoctorStatus,
    Gender,
    LicenseVerificationStatus,
)


def _pg_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda cls: [member.value for member in cls],
    )


_doctor_status_enum = _pg_enum(DoctorStatus, "doctor_status_enum")
_gender_enum = _pg_enum(Gender, "gender_enum")
_license_verification_status_enum = _pg_enum(
    LicenseVerificationStatus, "license_verification_status_enum"
)
_day_of_week_enum = _pg_enum(DayOfWeek, "day_of_week_enum")


class DoctorModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "doctors"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DoctorStatus] = mapped_column(
        _doctor_status_enum, nullable=False, default=DoctorStatus.ACTIVE
    )
    joining_date: Mapped[date] = mapped_column(nullable=False)

    __table_args__ = (
        Index(
            "uq_doctors_organization_id_employee_id",
            "organization_id",
            "employee_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_doctors_user_id",
            "user_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_doctors_organization_id", "organization_id"),
    )


class DoctorProfileModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "doctor_profiles"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    gender: Mapped[Gender] = mapped_column(_gender_enum, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, default=None)
    email: Mapped[str | None] = mapped_column(CITEXT, default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    biography: Mapped[str | None] = mapped_column(Text, default=None)
    years_of_experience: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    qualification: Mapped[str | None] = mapped_column(Text, default=None)
    consultation_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)
    profile_photo_url: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_doctor_profiles_doctor_id",
            "doctor_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint("years_of_experience >= 0", name="years_of_experience_nonneg"),
    )


class DoctorLicenseModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "doctor_licenses"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    license_number: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_authority: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    issue_date: Mapped[date] = mapped_column(nullable=False)
    expiry_date: Mapped[date] = mapped_column(nullable=False)
    verification_status: Mapped[LicenseVerificationStatus] = mapped_column(
        _license_verification_status_enum, nullable=False, default=LicenseVerificationStatus.PENDING
    )

    __table_args__ = (
        Index(
            "uq_doctor_licenses_license_number",
            "license_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_doctor_licenses_doctor_id", "doctor_id"),
        CheckConstraint("expiry_date > issue_date", name="expiry_after_issue"),
    )


class DoctorSpecializationModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "doctor_specializations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    specialization_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    years_of_experience: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    __table_args__ = (
        Index(
            "uq_doctor_specializations_primary_per_doctor",
            "doctor_id",
            unique=True,
            postgresql_where=text("is_primary AND deleted_at IS NULL"),
        ),
        Index("ix_doctor_specializations_doctor_id", "doctor_id"),
        CheckConstraint("years_of_experience >= 0", name="specialization_years_nonneg"),
    )


class DoctorScheduleModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "doctor_schedules"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[DayOfWeek] = mapped_column(_day_of_week_enum, nullable=False)
    start_time: Mapped[time] = mapped_column(nullable=False)
    end_time: Mapped[time] = mapped_column(nullable=False)
    break_start: Mapped[time | None] = mapped_column(default=None)
    break_end: Mapped[time | None] = mapped_column(default=None)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_doctor_schedules_doctor_id_day_of_week", "doctor_id", "day_of_week"),
        CheckConstraint("start_time < end_time", name="start_before_end"),
    )
