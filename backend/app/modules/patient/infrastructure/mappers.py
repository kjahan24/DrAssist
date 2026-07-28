"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.patient.domain.entities import Patient
from app.modules.patient.infrastructure.models import PatientModel
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
