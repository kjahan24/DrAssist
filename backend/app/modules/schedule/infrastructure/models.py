"""SQLAlchemy ORM models for the Schedule/Availability module.

Two tables: `doctor_availabilities`, `doctor_time_off_periods`. See
`app.modules.schedule.container` for the module's scope note — in
particular, why `doctor_availabilities` is deliberately *not* named
`doctor_schedules`: that name is already taken by the pre-existing,
differently-shaped `app.modules.doctor.infrastructure.models
.DoctorScheduleModel`, which this migration does not touch.

`organization_id`/`doctor_id` carry real foreign keys to
`organizations.id`/`doctors.id` on both tables — brand-new columns on
brand-new tables, so there is no backward-compatibility reason to defer
them; neither `organizations` nor `doctors` is modified by this
migration. Both use `ON DELETE RESTRICT`, matching every other module's
own treatment of `organization_id`/`doctor_id`.

"End time must be later than start time" has a `CHECK` constraint on
both tables (defense-in-depth alongside each entity's own
`__post_init__` validation), the same treatment
`doctor_schedules.start_time`/`end_time` and
`appointments.start_time`/`end_time` already receive. "Slot duration
must be greater than zero" has its own `CHECK` constraint on
`doctor_availabilities`.

There is no `CHECK`/unique constraint enforcing "no overlapping
schedules"/"no overlapping time-off": both are cross-row invariants a
`CHECK` constraint cannot express, and — following the same precedent
`doctor_schedules` itself already sets — neither uses a Postgres
`EXCLUDE` constraint either; both are enforced exclusively at the
application layer. There is likewise no `CHECK` constraint for "Doctor
and Organization must match": that requires reading another table's
data, which a `CHECK` constraint cannot do either.
"""

import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.schedule.domain.enums import Weekday

_weekday_enum = pg_enum(Weekday, "doctor_availability_weekday_enum")


class DoctorScheduleModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "doctor_availabilities"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    weekday: Mapped[Weekday] = mapped_column(_weekday_enum, nullable=False)
    start_time: Mapped[time] = mapped_column(nullable=False)
    end_time: Mapped[time] = mapped_column(nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_doctor_availabilities_organization_id", "organization_id"),
        Index("ix_doctor_availabilities_doctor_id", "doctor_id"),
        Index("ix_doctor_availabilities_doctor_id_weekday", "doctor_id", "weekday"),
        CheckConstraint("end_time > start_time", name="end_time_after_start_time"),
        CheckConstraint("slot_duration_minutes > 0", name="slot_duration_positive"),
    )


class DoctorTimeOffModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "doctor_time_off_periods"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False
    )
    start_datetime: Mapped[datetime] = mapped_column(nullable=False)
    end_datetime: Mapped[datetime] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index("ix_doctor_time_off_periods_organization_id", "organization_id"),
        Index("ix_doctor_time_off_periods_doctor_id", "doctor_id"),
        CheckConstraint("end_datetime > start_datetime", name="end_after_start"),
    )
