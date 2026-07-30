"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.infrastructure.models import AppointmentModel


def appointment_to_domain(model: AppointmentModel) -> Appointment:
    return Appointment(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        doctor_id=model.doctor_id,
        appointment_number=model.appointment_number,
        appointment_date=model.appointment_date,
        start_time=model.start_time,
        end_time=model.end_time,
        appointment_type=model.appointment_type,
        status=model.status,
        reason_for_visit=model.reason_for_visit,
        notes=model.notes,
        booked_by_user_id=model.booked_by_user_id,
        visit_id=model.visit_id,
        checked_in_at=model.checked_in_at,
        completed_at=model.completed_at,
        cancelled_at=model.cancelled_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_appointment_to_model(entity: Appointment, model: AppointmentModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.doctor_id = entity.doctor_id
    model.appointment_number = entity.appointment_number
    model.appointment_date = entity.appointment_date
    model.start_time = entity.start_time
    model.end_time = entity.end_time
    model.appointment_type = entity.appointment_type
    model.status = entity.status
    model.reason_for_visit = entity.reason_for_visit
    model.notes = entity.notes
    model.booked_by_user_id = entity.booked_by_user_id
    model.visit_id = entity.visit_id
    model.checked_in_at = entity.checked_in_at
    model.completed_at = entity.completed_at
    model.cancelled_at = entity.cancelled_at
