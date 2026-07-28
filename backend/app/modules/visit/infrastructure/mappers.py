"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.infrastructure.models import PatientVisitModel


def patient_visit_to_domain(model: PatientVisitModel) -> PatientVisit:
    return PatientVisit(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        doctor_id=model.doctor_id,
        visit_number=model.visit_number,
        appointment_id=model.appointment_id,
        visit_type=model.visit_type,
        visit_status=model.visit_status,
        priority=model.priority,
        visit_date=model.visit_date,
        check_in_time=model.check_in_time,
        consultation_start_time=model.consultation_start_time,
        consultation_end_time=model.consultation_end_time,
        check_out_time=model.check_out_time,
        chief_complaint_summary=model.chief_complaint_summary,
        reason_for_visit=model.reason_for_visit,
        room_number=model.room_number,
        follow_up_required=model.follow_up_required,
        follow_up_date=model.follow_up_date,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_patient_visit_to_model(entity: PatientVisit, model: PatientVisitModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.doctor_id = entity.doctor_id
    model.visit_number = entity.visit_number
    model.appointment_id = entity.appointment_id
    model.visit_type = entity.visit_type
    model.visit_status = entity.visit_status
    model.priority = entity.priority
    model.visit_date = entity.visit_date
    model.check_in_time = entity.check_in_time
    model.consultation_start_time = entity.consultation_start_time
    model.consultation_end_time = entity.consultation_end_time
    model.check_out_time = entity.check_out_time
    model.chief_complaint_summary = entity.chief_complaint_summary
    model.reason_for_visit = entity.reason_for_visit
    model.room_number = entity.room_number
    model.follow_up_required = entity.follow_up_required
    model.follow_up_date = entity.follow_up_date
    model.notes = entity.notes
