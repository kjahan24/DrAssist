"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.schedule.domain.entities import DoctorSchedule, DoctorTimeOff
from app.modules.schedule.infrastructure.models import DoctorScheduleModel, DoctorTimeOffModel


def doctor_schedule_to_domain(model: DoctorScheduleModel) -> DoctorSchedule:
    return DoctorSchedule(
        id=model.id,
        organization_id=model.organization_id,
        doctor_id=model.doctor_id,
        weekday=model.weekday,
        start_time=model.start_time,
        end_time=model.end_time,
        slot_duration_minutes=model.slot_duration_minutes,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_schedule_to_model(entity: DoctorSchedule, model: DoctorScheduleModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.doctor_id = entity.doctor_id
    model.weekday = entity.weekday
    model.start_time = entity.start_time
    model.end_time = entity.end_time
    model.slot_duration_minutes = entity.slot_duration_minutes
    model.is_active = entity.is_active


def doctor_time_off_to_domain(model: DoctorTimeOffModel) -> DoctorTimeOff:
    return DoctorTimeOff(
        id=model.id,
        organization_id=model.organization_id,
        doctor_id=model.doctor_id,
        start_datetime=model.start_datetime,
        end_datetime=model.end_datetime,
        reason=model.reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_doctor_time_off_to_model(entity: DoctorTimeOff, model: DoctorTimeOffModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.doctor_id = entity.doctor_id
    model.start_datetime = entity.start_datetime
    model.end_datetime = entity.end_datetime
    model.reason = entity.reason
