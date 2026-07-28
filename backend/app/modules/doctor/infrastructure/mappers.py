"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.doctor.domain.entities import (
    Doctor,
    DoctorLicense,
    DoctorProfile,
    DoctorSchedule,
    DoctorSpecialization,
)
from app.modules.doctor.infrastructure.models import (
    DoctorLicenseModel,
    DoctorModel,
    DoctorProfileModel,
    DoctorScheduleModel,
    DoctorSpecializationModel,
)
from app.shared.domain.common_value_objects import EmailAddress

# --- Doctor ----------------------------------------------------------------


def doctor_to_domain(model: DoctorModel) -> Doctor:
    return Doctor(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        employee_id=model.employee_id,
        joining_date=model.joining_date,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_to_model(entity: Doctor, model: DoctorModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.user_id = entity.user_id
    model.employee_id = entity.employee_id
    model.joining_date = entity.joining_date
    model.status = entity.status


# --- DoctorProfile -----------------------------------------------------


def doctor_profile_to_domain(model: DoctorProfileModel) -> DoctorProfile:
    return DoctorProfile(
        id=model.id,
        doctor_id=model.doctor_id,
        full_name=model.full_name,
        gender=model.gender,
        date_of_birth=model.date_of_birth,
        phone=model.phone,
        email=EmailAddress(model.email) if model.email else None,
        address=model.address,
        biography=model.biography,
        years_of_experience=model.years_of_experience,
        qualification=model.qualification,
        consultation_fee=model.consultation_fee,
        profile_photo_url=model.profile_photo_url,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_profile_to_model(entity: DoctorProfile, model: DoctorProfileModel) -> None:
    model.id = entity.id
    model.doctor_id = entity.doctor_id
    model.full_name = entity.full_name
    model.gender = entity.gender
    model.date_of_birth = entity.date_of_birth
    model.phone = entity.phone
    model.email = str(entity.email) if entity.email else None
    model.address = entity.address
    model.biography = entity.biography
    model.years_of_experience = entity.years_of_experience
    model.qualification = entity.qualification
    model.consultation_fee = entity.consultation_fee
    model.profile_photo_url = entity.profile_photo_url


# --- DoctorLicense -----------------------------------------------------


def doctor_license_to_domain(model: DoctorLicenseModel) -> DoctorLicense:
    return DoctorLicense(
        id=model.id,
        doctor_id=model.doctor_id,
        license_number=model.license_number,
        issuing_authority=model.issuing_authority,
        country=model.country,
        issue_date=model.issue_date,
        expiry_date=model.expiry_date,
        verification_status=model.verification_status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_license_to_model(entity: DoctorLicense, model: DoctorLicenseModel) -> None:
    model.id = entity.id
    model.doctor_id = entity.doctor_id
    model.license_number = entity.license_number
    model.issuing_authority = entity.issuing_authority
    model.country = entity.country
    model.issue_date = entity.issue_date
    model.expiry_date = entity.expiry_date
    model.verification_status = entity.verification_status


# --- DoctorSpecialization ------------------------------------------------


def doctor_specialization_to_domain(model: DoctorSpecializationModel) -> DoctorSpecialization:
    return DoctorSpecialization(
        id=model.id,
        organization_id=model.organization_id,
        doctor_id=model.doctor_id,
        specialization_name=model.specialization_name,
        is_primary=model.is_primary,
        years_of_experience=model.years_of_experience,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_specialization_to_model(
    entity: DoctorSpecialization, model: DoctorSpecializationModel
) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.doctor_id = entity.doctor_id
    model.specialization_name = entity.specialization_name
    model.is_primary = entity.is_primary
    model.years_of_experience = entity.years_of_experience


# --- DoctorSchedule ------------------------------------------------------


def doctor_schedule_to_domain(model: DoctorScheduleModel) -> DoctorSchedule:
    return DoctorSchedule(
        id=model.id,
        doctor_id=model.doctor_id,
        day_of_week=model.day_of_week,
        start_time=model.start_time,
        end_time=model.end_time,
        break_start=model.break_start,
        break_end=model.break_end,
        is_available=model.is_available,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_schedule_to_model(entity: DoctorSchedule, model: DoctorScheduleModel) -> None:
    model.id = entity.id
    model.doctor_id = entity.doctor_id
    model.day_of_week = entity.day_of_week
    model.start_time = entity.start_time
    model.end_time = entity.end_time
    model.break_start = entity.break_start
    model.break_end = entity.break_end
    model.is_available = entity.is_available
