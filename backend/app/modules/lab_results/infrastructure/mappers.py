"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.infrastructure.models import LabResultItemModel, LabResultModel


def lab_result_to_domain(model: LabResultModel) -> LabResult:
    return LabResult(
        id=model.id,
        organization_id=model.organization_id,
        lab_order_id=model.lab_order_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        result_number=model.result_number,
        reported_at=model.reported_at,
        status=model.status,
        laboratory_name=model.laboratory_name,
        comments=model.comments,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_lab_result_to_model(entity: LabResult, model: LabResultModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.lab_order_id = entity.lab_order_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.result_number = entity.result_number
    model.reported_at = entity.reported_at
    model.status = entity.status
    model.laboratory_name = entity.laboratory_name
    model.comments = entity.comments


def lab_result_item_to_domain(model: LabResultItemModel) -> LabResultItem:
    return LabResultItem(
        id=model.id,
        lab_result_id=model.lab_result_id,
        lab_order_item_id=model.lab_order_item_id,
        test_code=model.test_code,
        test_name=model.test_name,
        result_value=model.result_value,
        result_unit=model.result_unit,
        reference_range=model.reference_range,
        abnormal_flag=model.abnormal_flag,
        interpretation=model.interpretation,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_lab_result_item_to_model(entity: LabResultItem, model: LabResultItemModel) -> None:
    model.id = entity.id
    model.lab_result_id = entity.lab_result_id
    model.lab_order_item_id = entity.lab_order_item_id
    model.test_code = entity.test_code
    model.test_name = entity.test_name
    model.result_value = entity.result_value
    model.result_unit = entity.result_unit
    model.reference_range = entity.reference_range
    model.abnormal_flag = entity.abnormal_flag
    model.interpretation = entity.interpretation
