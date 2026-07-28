"""SQLAlchemy ORM models for the Patient module.

Four tables: `patients`, `patient_contacts`, `emergency_contacts`,
`insurances` (all three many-to-one with `patients`). See
`app.modules.patient.container` for the module's scope note.

`patients.organization_id` carries a real foreign key to
`organizations.id` — like the Doctor module's tables, this is a brand-new
column on a brand-new table, so there is no backward-compatibility
reason to defer it. Neither `organizations` nor any prior module's tables
are modified by these migrations.
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, SmallInteger, Text, text
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
from app.modules.patient.domain.enums import (
    BloodGroup,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
)

_patient_status_enum = pg_enum(PatientStatus, "patient_status_enum")
_gender_enum = pg_enum(Gender, "patient_gender_enum")
_blood_group_enum = pg_enum(BloodGroup, "blood_group_enum")
_marital_status_enum = pg_enum(MaritalStatus, "marital_status_enum")
_contact_type_enum = pg_enum(ContactType, "contact_type_enum")
_insurance_status_enum = pg_enum(InsuranceStatus, "insurance_status_enum")


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


class PatientContactModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "patient_contacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    contact_type: Mapped[ContactType] = mapped_column(_contact_type_enum, nullable=False)
    phone_number: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT, default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index(
            "uq_patient_contacts_primary_per_type",
            "patient_id",
            "contact_type",
            unique=True,
            postgresql_where=text("is_primary AND deleted_at IS NULL"),
        ),
        Index("ix_patient_contacts_patient_id", "patient_id"),
    )


class EmergencyContactModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "emergency_contacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    relationship: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT, default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    priority: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index(
            "uq_emergency_contacts_primary_per_patient",
            "patient_id",
            unique=True,
            postgresql_where=text("is_primary AND deleted_at IS NULL"),
        ),
        Index("ix_emergency_contacts_patient_id", "patient_id"),
    )


class InsuranceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin):
    __tablename__ = "insurances"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_number: Mapped[str] = mapped_column(Text, nullable=False)
    member_id: Mapped[str | None] = mapped_column(Text, default=None)
    group_number: Mapped[str | None] = mapped_column(Text, default=None)
    coverage_type: Mapped[str | None] = mapped_column(Text, default=None)
    effective_date: Mapped[date] = mapped_column(nullable=False)
    expiry_date: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[InsuranceStatus] = mapped_column(
        _insurance_status_enum, nullable=False, default=InsuranceStatus.ACTIVE
    )

    __table_args__ = (
        Index("ix_insurances_patient_id", "patient_id"),
        CheckConstraint("expiry_date > effective_date", name="expiry_after_effective"),
    )
