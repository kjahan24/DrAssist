"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.infrastructure.models import ClinicalReasoningModel


def clinical_reasoning_to_domain(model: ClinicalReasoningModel) -> ClinicalReasoning:
    return ClinicalReasoning(
        id=model.id,
        organization_id=model.organization_id,
        clinical_note_id=model.clinical_note_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        reasoning_source=model.reasoning_source,
        reasoning_text=model.reasoning_text,
        ai_generated=model.ai_generated,
        review_status=model.review_status,
        reviewed_by_doctor=model.reviewed_by_doctor,
        confidence_score=model.confidence_score,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_clinical_reasoning_to_model(
    entity: ClinicalReasoning, model: ClinicalReasoningModel
) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.clinical_note_id = entity.clinical_note_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.reasoning_source = entity.reasoning_source
    model.reasoning_text = entity.reasoning_text
    model.ai_generated = entity.ai_generated
    model.review_status = entity.review_status
    model.reviewed_by_doctor = entity.reviewed_by_doctor
    model.confidence_score = entity.confidence_score
