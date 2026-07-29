"""ORM model ↔ domain entity mapping.

The only place in the module that knows both shapes. Domain entities
never see an ORM instance; ORM instances never see a domain entity.
"""

from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.infrastructure.models import SOAPNoteModel


def soap_note_to_domain(model: SOAPNoteModel) -> SOAPNote:
    return SOAPNote(
        id=model.id,
        organization_id=model.organization_id,
        clinical_note_id=model.clinical_note_id,
        patient_id=model.patient_id,
        visit_id=model.visit_id,
        doctor_id=model.doctor_id,
        chief_complaint=model.chief_complaint,
        history_of_present_illness=model.history_of_present_illness,
        review_of_systems=model.review_of_systems,
        physical_examination=model.physical_examination,
        vital_sign_summary=model.vital_sign_summary,
        assessment=model.assessment,
        plan=model.plan,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_soap_note_to_model(entity: SOAPNote, model: SOAPNoteModel) -> None:
    model.id = entity.id
    model.organization_id = entity.organization_id
    model.clinical_note_id = entity.clinical_note_id
    model.patient_id = entity.patient_id
    model.visit_id = entity.visit_id
    model.doctor_id = entity.doctor_id
    model.chief_complaint = entity.chief_complaint
    model.history_of_present_illness = entity.history_of_present_illness
    model.review_of_systems = entity.review_of_systems
    model.physical_examination = entity.physical_examination
    model.vital_sign_summary = entity.vital_sign_summary
    model.assessment = entity.assessment
    model.plan = entity.plan
