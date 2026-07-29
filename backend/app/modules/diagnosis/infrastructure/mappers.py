"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.diagnosis.domain.entities import VisitDiagnosis
from app.modules.diagnosis.infrastructure.models import VisitDiagnosisModel


def visit_diagnosis_to_domain(model: VisitDiagnosisModel) -> VisitDiagnosis:
    return VisitDiagnosis(
        id=model.id,
        organization_id=model.organization_id,
        visit_id=model.visit_id,
        sequence_number=model.sequence_number,
        diagnosis_name=model.diagnosis_name,
        diagnosis_type=model.diagnosis_type,
        diagnosed_at=model.diagnosed_at,
        icd10_code=model.icd10_code,
        diagnosis_status=model.diagnosis_status,
        clinical_notes=model.clinical_notes,
        diagnosed_by=model.diagnosed_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_visit_diagnosis_to_model(entity: VisitDiagnosis, model: VisitDiagnosisModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.visit_id = entity.visit_id
    model.sequence_number = entity.sequence_number
    model.diagnosis_name = entity.diagnosis_name
    model.diagnosis_type = entity.diagnosis_type
    model.diagnosed_at = entity.diagnosed_at
    model.icd10_code = entity.icd10_code
    model.diagnosis_status = entity.diagnosis_status
    model.clinical_notes = entity.clinical_notes
    model.diagnosed_by = entity.diagnosed_by
