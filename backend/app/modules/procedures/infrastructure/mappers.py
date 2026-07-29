"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.procedures.domain.entities import VisitProcedure
from app.modules.procedures.infrastructure.models import VisitProcedureModel


def visit_procedure_to_domain(model: VisitProcedureModel) -> VisitProcedure:
    return VisitProcedure(
        id=model.id,
        organization_id=model.organization_id,
        visit_id=model.visit_id,
        sequence_number=model.sequence_number,
        procedure_name=model.procedure_name,
        procedure_code=model.procedure_code,
        procedure_category=model.procedure_category,
        procedure_status=model.procedure_status,
        performed_by=model.performed_by,
        performed_at=model.performed_at,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_visit_procedure_to_model(entity: VisitProcedure, model: VisitProcedureModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.visit_id = entity.visit_id
    model.sequence_number = entity.sequence_number
    model.procedure_name = entity.procedure_name
    model.procedure_code = entity.procedure_code
    model.procedure_category = entity.procedure_category
    model.procedure_status = entity.procedure_status
    model.performed_by = entity.performed_by
    model.performed_at = entity.performed_at
    model.notes = entity.notes
