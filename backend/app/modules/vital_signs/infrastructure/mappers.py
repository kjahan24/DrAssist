"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.vital_signs.domain.entities import VisitVitalSigns
from app.modules.vital_signs.domain.value_objects import BloodPressure
from app.modules.vital_signs.infrastructure.models import VisitVitalSignsModel


def visit_vital_signs_to_domain(model: VisitVitalSignsModel) -> VisitVitalSigns:
    return VisitVitalSigns(
        id=model.id,
        organization_id=model.organization_id,
        visit_id=model.visit_id,
        recorded_by=model.recorded_by,
        height_cm=model.height_cm,
        weight_kg=model.weight_kg,
        temperature_c=model.temperature_c,
        pulse_bpm=model.pulse_bpm,
        respiratory_rate=model.respiratory_rate,
        blood_pressure=BloodPressure(systolic=model.systolic_bp, diastolic=model.diastolic_bp),
        spo2=model.spo2,
        blood_glucose=model.blood_glucose,
        pain_score=model.pain_score,
        recorded_at=model.recorded_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_visit_vital_signs_to_model(entity: VisitVitalSigns, model: VisitVitalSignsModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.visit_id = entity.visit_id
    model.recorded_by = entity.recorded_by
    model.height_cm = entity.height_cm
    model.weight_kg = entity.weight_kg
    model.bmi = entity.bmi
    model.temperature_c = entity.temperature_c
    model.pulse_bpm = entity.pulse_bpm
    model.respiratory_rate = entity.respiratory_rate
    model.systolic_bp = entity.blood_pressure.systolic
    model.diastolic_bp = entity.blood_pressure.diastolic
    model.spo2 = entity.spo2
    model.blood_glucose = entity.blood_glucose
    model.pain_score = entity.pain_score
    model.recorded_at = entity.recorded_at
