"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.infrastructure.models import DoctorReviewModel


def doctor_review_to_domain(model: DoctorReviewModel) -> DoctorReview:
    return DoctorReview(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        clinical_note_id=model.clinical_note_id,
        review_status=model.review_status,
        review_comment=model.review_comment,
        reviewed_at=model.reviewed_at,
        approved_clinical_note=model.approved_clinical_note,
        approved_soap_note=model.approved_soap_note,
        approved_prescription=model.approved_prescription,
        approved_lab_orders=model.approved_lab_orders,
        approved_lab_results=model.approved_lab_results,
        approved_reasoning=model.approved_reasoning,
        approved_differential_diagnosis=model.approved_differential_diagnosis,
        approved_icd10=model.approved_icd10,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_review_to_model(entity: DoctorReview, model: DoctorReviewModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.clinical_note_id = entity.clinical_note_id
    model.review_status = entity.review_status
    model.review_comment = entity.review_comment
    model.reviewed_at = entity.reviewed_at
    model.approved_clinical_note = entity.approved_clinical_note
    model.approved_soap_note = entity.approved_soap_note
    model.approved_prescription = entity.approved_prescription
    model.approved_lab_orders = entity.approved_lab_orders
    model.approved_lab_results = entity.approved_lab_results
    model.approved_reasoning = entity.approved_reasoning
    model.approved_differential_diagnosis = entity.approved_differential_diagnosis
    model.approved_icd10 = entity.approved_icd10
