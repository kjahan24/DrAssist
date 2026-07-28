"""SQLAlchemy ORM models for the Patient module.

Seven tables: `patients`, `patient_contacts`, `emergency_contacts`,
`insurances`, `patient_allergies`, `patient_medications`,
`patient_medical_conditions` (all six many-to-one with `patients`). See
`app.modules.patient.container` for the module's scope note.

`patients.organization_id` carries a real foreign key to
`organizations.id` — like the Doctor module's tables, this is a brand-new
column on a brand-new table, so there is no backward-compatibility
reason to defer it. `patient_allergies.verified_by`,
`patient_medications.prescribed_by`, and
`patient_medical_conditions.diagnosed_by` carry real foreign keys to
`doctors.id` (the Doctor module's table) — see those columns' own
comments below for why they use `ON DELETE SET NULL` rather than
`RESTRICT`. Neither `organizations`, `doctors`, nor any prior module's
tables are modified by these migrations.
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
    AdherenceStatus,
    AllergySeverity,
    AllergyStatus,
    AllergyType,
    BloodGroup,
    ConditionSeverity,
    ConditionStatus,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
    RouteOfAdministration,
)

_patient_status_enum = pg_enum(PatientStatus, "patient_status_enum")
_gender_enum = pg_enum(Gender, "patient_gender_enum")
_blood_group_enum = pg_enum(BloodGroup, "blood_group_enum")
_marital_status_enum = pg_enum(MaritalStatus, "marital_status_enum")
_contact_type_enum = pg_enum(ContactType, "contact_type_enum")
_insurance_status_enum = pg_enum(InsuranceStatus, "insurance_status_enum")
_allergy_type_enum = pg_enum(AllergyType, "allergy_type_enum")
_allergy_severity_enum = pg_enum(AllergySeverity, "allergy_severity_enum")
_allergy_status_enum = pg_enum(AllergyStatus, "allergy_status_enum")
_route_of_administration_enum = pg_enum(RouteOfAdministration, "route_of_administration_enum")
_adherence_status_enum = pg_enum(AdherenceStatus, "adherence_status_enum")
_condition_severity_enum = pg_enum(ConditionSeverity, "condition_severity_enum")
_condition_status_enum = pg_enum(ConditionStatus, "condition_status_enum")


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


class PatientAllergyModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "patient_allergies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    allergy_type: Mapped[AllergyType] = mapped_column(_allergy_type_enum, nullable=False)
    allergen_name: Mapped[str] = mapped_column(CITEXT, nullable=False)
    severity: Mapped[AllergySeverity] = mapped_column(_allergy_severity_enum, nullable=False)
    reaction: Mapped[str | None] = mapped_column(Text, default=None)
    onset_date: Mapped[date | None] = mapped_column(default=None)
    status: Mapped[AllergyStatus] = mapped_column(
        _allergy_status_enum, nullable=False, default=AllergyStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    # References `doctors.id`, not the `AuditActorMixin` `created_by`/
    # `updated_by` columns above (those track who edited the row generically;
    # this tracks which doctor clinically verified the allergy). `SET NULL`
    # rather than `RESTRICT` so a doctor's record can still be removed
    # without being blocked by every allergy they've ever verified —
    # historical attribution is best-effort, not load-bearing, the same
    # reasoning `AuditActorMixin` itself documents for `created_by`/
    # `updated_by`.
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    verified_date: Mapped[date | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_patient_allergies_active_per_patient_and_allergen",
            "patient_id",
            "allergen_name",
            unique=True,
            postgresql_where=text("status = 'active' AND deleted_at IS NULL"),
        ),
        Index("ix_patient_allergies_patient_id", "patient_id"),
        CheckConstraint(
            "verified_date IS NULL OR verified_by IS NOT NULL",
            name="verified_date_requires_verified_by",
        ),
    )


class PatientMedicationModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "patient_medications"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    medication_name: Mapped[str] = mapped_column(Text, nullable=False)
    dosage: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[RouteOfAdministration] = mapped_column(
        _route_of_administration_enum, nullable=False
    )
    start_date: Mapped[date] = mapped_column(nullable=False)
    # References `doctors.id`, not the `AuditActorMixin` `created_by`/
    # `updated_by` columns above — see the identical reasoning on
    # `PatientAllergyModel.verified_by`. `SET NULL` rather than `RESTRICT`
    # for the same reason: a doctor's record can still be removed without
    # being blocked by every medication they've ever prescribed.
    prescribed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    generic_name: Mapped[str | None] = mapped_column(Text, default=None)
    brand_name: Mapped[str | None] = mapped_column(Text, default=None)
    dosage_unit: Mapped[str | None] = mapped_column(Text, default=None)
    frequency: Mapped[str | None] = mapped_column(Text, default=None)
    indication: Mapped[str | None] = mapped_column(Text, default=None)
    end_date: Mapped[date | None] = mapped_column(default=None)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    adherence_status: Mapped[AdherenceStatus] = mapped_column(
        _adherence_status_enum, nullable=False, default=AdherenceStatus.TAKING
    )
    instructions: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index("ix_patient_medications_patient_id", "patient_id"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="end_date_not_before_start_date"
        ),
        CheckConstraint(
            "is_current OR adherence_status != 'completed' OR end_date IS NOT NULL",
            name="end_date_required_for_completed",
        ),
    )


class PatientMedicalConditionModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "patient_medical_conditions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    condition_name: Mapped[str] = mapped_column(CITEXT, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[ConditionSeverity] = mapped_column(_condition_severity_enum, nullable=False)
    diagnosis_date: Mapped[date] = mapped_column(nullable=False)
    # References `doctors.id`, not the `AuditActorMixin` `created_by`/
    # `updated_by` columns above — see the identical reasoning on
    # `PatientAllergyModel.verified_by`. `SET NULL` rather than `RESTRICT`
    # for the same reason: a doctor's record can still be removed without
    # being blocked by every condition they've ever diagnosed.
    diagnosed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    icd10_code: Mapped[str | None] = mapped_column(Text, default=None)
    onset_date: Mapped[date | None] = mapped_column(default=None)
    status: Mapped[ConditionStatus] = mapped_column(
        _condition_status_enum, nullable=False, default=ConditionStatus.ACTIVE
    )
    is_chronic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_infectious: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    resolved_date: Mapped[date | None] = mapped_column(default=None)

    __table_args__ = (
        Index(
            "uq_patient_medical_conditions_active_per_patient_and_name",
            "patient_id",
            "condition_name",
            unique=True,
            postgresql_where=text("status = 'active' AND deleted_at IS NULL"),
        ),
        Index("ix_patient_medical_conditions_patient_id", "patient_id"),
        CheckConstraint(
            "resolved_date IS NULL OR resolved_date > diagnosis_date",
            name="resolved_after_diagnosis",
        ),
        CheckConstraint(
            "NOT is_chronic OR status != 'resolved' OR resolved_date IS NOT NULL",
            name="chronic_resolved_requires_date",
        ),
    )
