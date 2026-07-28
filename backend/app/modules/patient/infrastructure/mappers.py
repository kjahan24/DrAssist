"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.patient.domain.entities import (
    EmergencyContact,
    Insurance,
    Patient,
    PatientAllergy,
    PatientContact,
    PatientMedication,
)
from app.modules.patient.infrastructure.models import (
    EmergencyContactModel,
    InsuranceModel,
    PatientAllergyModel,
    PatientContactModel,
    PatientMedicationModel,
    PatientModel,
)
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


def patient_to_domain(model: PatientModel) -> Patient:
    return Patient(
        id=model.id,
        organization_id=model.organization_id,
        patient_number=model.patient_number,
        first_name=model.first_name,
        middle_name=model.middle_name,
        last_name=model.last_name,
        preferred_name=model.preferred_name,
        gender=model.gender,
        date_of_birth=model.date_of_birth,
        blood_group=model.blood_group,
        marital_status=model.marital_status,
        national_id=model.national_id,
        passport_number=model.passport_number,
        phone=PhoneNumber(model.phone) if model.phone else None,
        email=EmailAddress(model.email) if model.email else None,
        occupation=model.occupation,
        nationality=model.nationality,
        language=model.language,
        religion=model.religion,
        address_line_1=model.address_line_1,
        address_line_2=model.address_line_2,
        city=model.city,
        state=model.state,
        postal_code=model.postal_code,
        country=model.country,
        photo_url=model.photo_url,
        remarks=model.remarks,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_patient_to_model(entity: Patient, model: PatientModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_number = entity.patient_number
    model.first_name = entity.first_name
    model.middle_name = entity.middle_name
    model.last_name = entity.last_name
    model.preferred_name = entity.preferred_name
    model.gender = entity.gender
    model.date_of_birth = entity.date_of_birth
    model.blood_group = entity.blood_group
    model.marital_status = entity.marital_status
    model.national_id = entity.national_id
    model.passport_number = entity.passport_number
    model.phone = str(entity.phone) if entity.phone else None
    model.email = str(entity.email) if entity.email else None
    model.occupation = entity.occupation
    model.nationality = entity.nationality
    model.language = entity.language
    model.religion = entity.religion
    model.address_line_1 = entity.address_line_1
    model.address_line_2 = entity.address_line_2
    model.city = entity.city
    model.state = entity.state
    model.postal_code = entity.postal_code
    model.country = entity.country
    model.photo_url = entity.photo_url
    model.remarks = entity.remarks
    model.status = entity.status


# --- PatientContact ----------------------------------------------------


def patient_contact_to_domain(model: PatientContactModel) -> PatientContact:
    return PatientContact(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        contact_type=model.contact_type,
        phone_number=PhoneNumber(model.phone_number),
        email=EmailAddress(model.email) if model.email else None,
        is_primary=model.is_primary,
        is_verified=model.is_verified,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_patient_contact_to_model(entity: PatientContact, model: PatientContactModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.contact_type = entity.contact_type
    model.phone_number = str(entity.phone_number)
    model.email = str(entity.email) if entity.email else None
    model.is_primary = entity.is_primary
    model.is_verified = entity.is_verified


# --- EmergencyContact ----------------------------------------------------


def emergency_contact_to_domain(model: EmergencyContactModel) -> EmergencyContact:
    return EmergencyContact(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        full_name=model.full_name,
        relationship=model.relationship,
        phone_number=PhoneNumber(model.phone_number),
        email=EmailAddress(model.email) if model.email else None,
        address=model.address,
        priority=model.priority,
        is_primary=model.is_primary,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_emergency_contact_to_model(
    entity: EmergencyContact, model: EmergencyContactModel
) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.full_name = entity.full_name
    model.relationship = entity.relationship
    model.phone_number = str(entity.phone_number)
    model.email = str(entity.email) if entity.email else None
    model.address = entity.address
    model.priority = entity.priority
    model.is_primary = entity.is_primary


# --- Insurance ----------------------------------------------------------


def insurance_to_domain(model: InsuranceModel) -> Insurance:
    return Insurance(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        provider_name=model.provider_name,
        policy_number=model.policy_number,
        member_id=model.member_id,
        group_number=model.group_number,
        coverage_type=model.coverage_type,
        effective_date=model.effective_date,
        expiry_date=model.expiry_date,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_insurance_to_model(entity: Insurance, model: InsuranceModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.provider_name = entity.provider_name
    model.policy_number = entity.policy_number
    model.member_id = entity.member_id
    model.group_number = entity.group_number
    model.coverage_type = entity.coverage_type
    model.effective_date = entity.effective_date
    model.expiry_date = entity.expiry_date
    model.status = entity.status


# --- PatientAllergy ------------------------------------------------------


def patient_allergy_to_domain(model: PatientAllergyModel) -> PatientAllergy:
    return PatientAllergy(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        allergy_type=model.allergy_type,
        allergen_name=model.allergen_name,
        severity=model.severity,
        reaction=model.reaction,
        onset_date=model.onset_date,
        status=model.status,
        notes=model.notes,
        verified_by=model.verified_by,
        verified_date=model.verified_date,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_patient_allergy_to_model(entity: PatientAllergy, model: PatientAllergyModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.allergy_type = entity.allergy_type
    model.allergen_name = entity.allergen_name
    model.severity = entity.severity
    model.reaction = entity.reaction
    model.onset_date = entity.onset_date
    model.status = entity.status
    model.notes = entity.notes
    model.verified_by = entity.verified_by
    model.verified_date = entity.verified_date


# --- PatientMedication -----------------------------------------------------


def patient_medication_to_domain(model: PatientMedicationModel) -> PatientMedication:
    return PatientMedication(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        medication_name=model.medication_name,
        dosage=model.dosage,
        route=model.route,
        start_date=model.start_date,
        prescribed_by=model.prescribed_by,
        generic_name=model.generic_name,
        brand_name=model.brand_name,
        dosage_unit=model.dosage_unit,
        frequency=model.frequency,
        indication=model.indication,
        end_date=model.end_date,
        is_current=model.is_current,
        adherence_status=model.adherence_status,
        instructions=model.instructions,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_patient_medication_to_model(
    entity: PatientMedication, model: PatientMedicationModel
) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.medication_name = entity.medication_name
    model.dosage = entity.dosage
    model.route = entity.route
    model.start_date = entity.start_date
    model.prescribed_by = entity.prescribed_by
    model.generic_name = entity.generic_name
    model.brand_name = entity.brand_name
    model.dosage_unit = entity.dosage_unit
    model.frequency = entity.frequency
    model.indication = entity.indication
    model.end_date = entity.end_date
    model.is_current = entity.is_current
    model.adherence_status = entity.adherence_status
    model.instructions = entity.instructions
    model.notes = entity.notes
