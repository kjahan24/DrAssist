"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
`Signature` is split across two columns (`signed_at`/`signed_by`) on
write and reassembled on read — present together or absent together, per
`ClinicalNote`'s own invariant.
"""

from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.value_objects import Signature
from app.modules.clinical_notes.infrastructure.models import ClinicalNoteModel


def clinical_note_to_domain(model: ClinicalNoteModel) -> ClinicalNote:
    signature = (
        Signature(signed_at=model.signed_at, signed_by=model.signed_by)
        if model.signed_at is not None and model.signed_by is not None
        else None
    )
    return ClinicalNote(
        id=model.id,
        organization_id=model.organization_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        note_number=model.note_number,
        note_type=model.note_type,
        status=model.status,
        encounter_datetime=model.encounter_datetime,
        chief_complaint_summary=model.chief_complaint_summary,
        history_summary=model.history_summary,
        examination_summary=model.examination_summary,
        assessment_summary=model.assessment_summary,
        plan_summary=model.plan_summary,
        ai_generated=model.ai_generated,
        ai_model=model.ai_model,
        ai_version=model.ai_version,
        signature=signature,
        locked_at=model.locked_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_clinical_note_to_model(entity: ClinicalNote, model: ClinicalNoteModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.note_number = entity.note_number
    model.note_type = entity.note_type
    model.status = entity.status
    model.encounter_datetime = entity.encounter_datetime
    model.chief_complaint_summary = entity.chief_complaint_summary
    model.history_summary = entity.history_summary
    model.examination_summary = entity.examination_summary
    model.assessment_summary = entity.assessment_summary
    model.plan_summary = entity.plan_summary
    model.ai_generated = entity.ai_generated
    model.ai_model = entity.ai_model
    model.ai_version = entity.ai_version
    model.signed_at = entity.signature.signed_at if entity.signature is not None else None
    model.signed_by = entity.signature.signed_by if entity.signature is not None else None
    model.locked_at = entity.locked_at
