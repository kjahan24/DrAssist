"""SQLAlchemy ORM model for the Patient module.

One table: `patients`. See `app.modules.patient.container` for the
module's scope note.

`patients.organization_id` carries a real foreign key to
`organizations.id` — like the Doctor module's tables, this is a brand-new
column on a brand-new table, so there is no backward-compatibility
reason to defer it. Neither `organizations` nor any prior module's tables
are modified by this migration.
"""

import uuid
from datetime import date

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.patient.domain.enums import BloodGroup, Gender, MaritalStatus, PatientStatus

_patient_status_enum = pg_enum(PatientStatus, "patient_status_enum")
_gender_enum = pg_enum(Gender, "patient_gender_enum")
_blood_group_enum = pg_enum(BloodGroup, "blood_group_enum")
_marital_status_enum = pg_enum(MaritalStatus, "marital_status_enum")


class PatientModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "patients"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_number: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    middle_name: Mapped[str | None] = mapped_column(Text, default=None)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(Text, default=None)
    gender: Mapped[Gender] = mapped_column(_gender_enum, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(nullable=False)
    blood_group: Mapped[BloodGroup | None] = mapped_column(_blood_group_enum, default=None)
    marital_status: Mapped[MaritalStatus | None] = mapped_column(_marital_status_enum, default=None)
    national_id: Mapped[str | None] = mapped_column(Text, default=None)
    passport_number: Mapped[str | None] = mapped_column(Text, default=None)
    phone: Mapped[str | None] = mapped_column(Text, default=None)
    email: Mapped[str | None] = mapped_column(CITEXT, default=None)
    occupation: Mapped[str | None] = mapped_column(Text, default=None)
    nationality: Mapped[str | None] = mapped_column(Text, default=None)
    language: Mapped[str | None] = mapped_column(Text, default=None)
    religion: Mapped[str | None] = mapped_column(Text, default=None)
    address_line_1: Mapped[str | None] = mapped_column(Text, default=None)
    address_line_2: Mapped[str | None] = mapped_column(Text, default=None)
    city: Mapped[str | None] = mapped_column(Text, default=None)
    state: Mapped[str | None] = mapped_column(Text, default=None)
    postal_code: Mapped[str | None] = mapped_column(Text, default=None)
    country: Mapped[str | None] = mapped_column(Text, default=None)
    photo_url: Mapped[str | None] = mapped_column(Text, default=None)
    remarks: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[PatientStatus] = mapped_column(
        _patient_status_enum, nullable=False, default=PatientStatus.ACTIVE
    )

    __table_args__ = (
        Index(
            "uq_patients_organization_id_patient_number",
            "organization_id",
            "patient_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_patients_organization_id", "organization_id"),
    )
