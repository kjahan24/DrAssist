"""Module composition root.

The one place `ClinicalNoteQueryPort` gets bound to its concrete
implementation (`ClinicalNoteFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's
`api/dependencies.py` calls `build_clinical_note_facade(session)` rather
than constructing `ClinicalNoteFacade` (or the repository) directly.

Scope note — this task builds the Clinical Notes module's **foundation**
only: the `ClinicalNote` entity (the master record for every future
clinical document), its repository, `CreateClinicalNote` (which confirms
the referenced visit exists via the Visit module's public facade, that
`patient_id` matches that visit's own patient, and that the authoring
`doctor_id` references a doctor in the same organization, and that
`note_number` is globally unique, before creating a note), and the
public query facade. It deliberately does **not** build any HTTP
endpoint, and does not modify the Authentication, Organization, Doctor,
Patient, Visit, Vital Signs, Chief Complaints, Diagnosis, Procedures, or
Attachments modules or their tables.

SOAP Note, Prescription, Lab Order, Lab Result, Imaging Report, Clinical
Reasoning, Differential Diagnosis, ICD-10 Coding, CPT Coding, AI
Copilot, Doctor Review, and Clinical Timeline are explicitly out of
scope for this task — they are expected to become their own modules,
each adding its own table with a `clinical_note_id` foreign key and
depending on `ClinicalNoteQueryPort` to confirm a note exists (and, for
Clinical Timeline, to list a patient's notes across visits) before
attaching to it. Nothing in this table needs to change for any of them.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clinical_notes.application.services.clinical_note_query_service import (
    ClinicalNoteQueryService,
)
from app.modules.clinical_notes.infrastructure.repositories import (
    SqlAlchemyClinicalNoteRepository,
)
from app.modules.clinical_notes.public.facade import ClinicalNoteFacade


def build_clinical_note_facade(session: AsyncSession) -> ClinicalNoteFacade:
    """Construct a `ClinicalNoteFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    clinical_note_repository = SqlAlchemyClinicalNoteRepository(session)

    query_service = ClinicalNoteQueryService(clinical_note_repository=clinical_note_repository)

    return ClinicalNoteFacade(query_service=query_service)
