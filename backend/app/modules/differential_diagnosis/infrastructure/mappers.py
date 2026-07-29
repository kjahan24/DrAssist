"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.infrastructure.models import DifferentialDiagnosisModel


def differential_diagnosis_to_domain(model: DifferentialDiagnosisModel) -> DifferentialDiagnosis:
    return DifferentialDiagnosis(
        id=model.id,
        organization_id=model.organization_id,
        clinical_note_id=model.clinical_note_id,
        clinical_reasoning_id=model.clinical_reasoning_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        diagnosis_name=model.diagnosis_name,
        diagnosis_source=model.diagnosis_source,
        ranking=model.ranking,
        review_status=model.review_status,
        likelihood_score=model.likelihood_score,
        supporting_evidence=model.supporting_evidence,
        excluded=model.excluded,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_differential_diagnosis_to_model(
    entity: DifferentialDiagnosis, model: DifferentialDiagnosisModel
) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.clinical_note_id = entity.clinical_note_id
    model.clinical_reasoning_id = entity.clinical_reasoning_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.diagnosis_name = entity.diagnosis_name
    model.diagnosis_source = entity.diagnosis_source
    model.ranking = entity.ranking
    model.review_status = entity.review_status
    model.likelihood_score = entity.likelihood_score
    model.supporting_evidence = entity.supporting_evidence
    model.excluded = entity.excluded
