"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.infrastructure.models import LabOrderItemModel, LabOrderModel


def lab_order_to_domain(model: LabOrderModel) -> LabOrder:
    return LabOrder(
        id=model.id,
        organization_id=model.organization_id,
        clinical_note_id=model.clinical_note_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        order_number=model.order_number,
        ordered_at=model.ordered_at,
        priority=model.priority,
        status=model.status,
        clinical_information=model.clinical_information,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_lab_order_to_model(entity: LabOrder, model: LabOrderModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.clinical_note_id = entity.clinical_note_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.order_number = entity.order_number
    model.ordered_at = entity.ordered_at
    model.priority = entity.priority
    model.status = entity.status
    model.clinical_information = entity.clinical_information
    model.notes = entity.notes


def lab_order_item_to_domain(model: LabOrderItemModel) -> LabOrderItem:
    return LabOrderItem(
        id=model.id,
        lab_order_id=model.lab_order_id,
        test_code=model.test_code,
        test_name=model.test_name,
        specimen_type=model.specimen_type,
        specimen_site=model.specimen_site,
        status=model.status,
        instructions=model.instructions,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_lab_order_item_to_model(entity: LabOrderItem, model: LabOrderItemModel) -> None:
    model.id = entity.id
    model.lab_order_id = entity.lab_order_id
    model.test_code = entity.test_code
    model.test_name = entity.test_name
    model.specimen_type = entity.specimen_type
    model.specimen_site = entity.specimen_site
    model.status = entity.status
    model.instructions = entity.instructions
