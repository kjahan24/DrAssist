"""ORM model <-> domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.infrastructure.models import PrescriptionItemModel, PrescriptionModel


def prescription_to_domain(model: PrescriptionModel) -> Prescription:
    return Prescription(
        id=model.id,
        organization_id=model.organization_id,
        clinical_note_id=model.clinical_note_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        prescription_number=model.prescription_number,
        prescription_date=model.prescription_date,
        status=model.status,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_prescription_to_model(entity: Prescription, model: PrescriptionModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.clinical_note_id = entity.clinical_note_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.prescription_number = entity.prescription_number
    model.prescription_date = entity.prescription_date
    model.status = entity.status
    model.notes = entity.notes


def prescription_item_to_domain(model: PrescriptionItemModel) -> PrescriptionItem:
    return PrescriptionItem(
        id=model.id,
        prescription_id=model.prescription_id,
        medication_name=model.medication_name,
        generic_name=model.generic_name,
        strength=model.strength,
        dosage=model.dosage,
        dosage_unit=model.dosage_unit,
        frequency=model.frequency,
        route=model.route,
        duration=model.duration,
        duration_unit=model.duration_unit,
        quantity=model.quantity,
        instructions=model.instructions,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_prescription_item_to_model(
    entity: PrescriptionItem, model: PrescriptionItemModel
) -> None:
    model.id = entity.id
    model.prescription_id = entity.prescription_id
    model.medication_name = entity.medication_name
    model.generic_name = entity.generic_name
    model.strength = entity.strength
    model.dosage = entity.dosage
    model.dosage_unit = entity.dosage_unit
    model.frequency = entity.frequency
    model.route = entity.route
    model.duration = entity.duration
    model.duration_unit = entity.duration_unit
    model.quantity = entity.quantity
    model.instructions = entity.instructions
