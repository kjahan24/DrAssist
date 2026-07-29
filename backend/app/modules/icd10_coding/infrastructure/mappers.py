"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.infrastructure.models import ICD10CodingModel


def icd10_coding_to_domain(model: ICD10CodingModel) -> ICD10Coding:
    return ICD10Coding(
        id=model.id,
        organization_id=model.organization_id,
        clinical_note_id=model.clinical_note_id,
        differential_diagnosis_id=model.differential_diagnosis_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        icd10_code=model.icd10_code,
        diagnosis_title=model.diagnosis_title,
        coding_source=model.coding_source,
        primary_code=model.primary_code,
        review_status=model.review_status,
        coding_notes=model.coding_notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_icd10_coding_to_model(entity: ICD10Coding, model: ICD10CodingModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.clinical_note_id = entity.clinical_note_id
    model.differential_diagnosis_id = entity.differential_diagnosis_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.icd10_code = entity.icd10_code
    model.diagnosis_title = entity.diagnosis_title
    model.coding_source = entity.coding_source
    model.primary_code = entity.primary_code
    model.review_status = entity.review_status
    model.coding_notes = entity.coding_notes
