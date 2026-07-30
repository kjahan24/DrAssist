"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.infrastructure.models import PatientHistoryModel


def patient_history_to_domain(model: PatientHistoryModel) -> PatientHistory:
    return PatientHistory(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_review_id=model.doctor_review_id,
        history_type=model.history_type,
        reference_type=model.reference_type,
        reference_id=model.reference_id,
        encounter_date=model.encounter_date,
        summary=model.summary,
        created_from_review=model.created_from_review,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_patient_history_to_model(entity: PatientHistory, model: PatientHistoryModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_review_id = entity.doctor_review_id
    model.history_type = entity.history_type
    model.reference_type = entity.reference_type
    model.reference_id = entity.reference_id
    model.encounter_date = entity.encounter_date
    model.summary = entity.summary
    model.created_from_review = entity.created_from_review
