"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.chief_complaints.domain.entities import VisitChiefComplaint
from app.modules.chief_complaints.infrastructure.models import VisitChiefComplaintModel


def visit_chief_complaint_to_domain(model: VisitChiefComplaintModel) -> VisitChiefComplaint:
    return VisitChiefComplaint(
        id=model.id,
        organization_id=model.organization_id,
        visit_id=model.visit_id,
        sequence_number=model.sequence_number,
        complaint=model.complaint,
        recorded_at=model.recorded_at,
        duration_value=model.duration_value,
        duration_unit=model.duration_unit,
        severity=model.severity,
        onset=model.onset,
        notes=model.notes,
        recorded_by=model.recorded_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_visit_chief_complaint_to_model(
    entity: VisitChiefComplaint, model: VisitChiefComplaintModel
) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.visit_id = entity.visit_id
    model.sequence_number = entity.sequence_number
    model.complaint = entity.complaint
    model.recorded_at = entity.recorded_at
    model.duration_value = entity.duration_value
    model.duration_unit = entity.duration_unit
    model.severity = entity.severity
    model.onset = entity.onset
    model.notes = entity.notes
    model.recorded_by = entity.recorded_by
